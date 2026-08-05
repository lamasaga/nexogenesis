from dataclasses import dataclass, field
from pathlib import Path
import re

from nexogenesis.models import Card, CardType, RelationType
from nexogenesis.yaml_utils import split_frontmatter

WIKILINK_RE = re.compile(r"\[\[([^\]|#/]+)")


@dataclass
class Store:
    cards_dir: Path
    cards: dict[str, Card] = field(default_factory=dict)
    by_domain: dict[str, list[str]] = field(default_factory=dict)
    conflicts_involving: dict[str, list[str]] = field(default_factory=dict)
    theories: list[str] = field(default_factory=list)

    def load(self) -> "Store":
        self.cards = {}
        self.by_domain = {}
        self.conflicts_involving = {}
        self.theories = []
        for path in sorted(self.cards_dir.glob("*.md")):
            if path.name.startswith("_"):
                continue
            text = path.read_text(encoding="utf-8")
            meta, body = split_frontmatter(text)
            if not meta or "id" not in meta:
                continue
            card = Card.from_dict(meta["id"], meta, body, str(path))
            self.cards[card.id] = card
            for d in card.domains:
                self.by_domain.setdefault(d, []).append(card.id)
            if card.theory_status:
                self.theories.append(card.id)
        self._build_conflict_index()
        return self

    def _build_conflict_index(self) -> None:
        self.conflicts_involving = {}
        for card in self.cards.values():
            if card.type != CardType.CONFLICT:
                continue
            for rel in card.relations:
                if rel.type == RelationType.INVOLVES:
                    self.conflicts_involving.setdefault(rel.target, []).append(card.id)

    def validate(self) -> tuple[list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []
        for card in self.cards.values():
            if not card.domains:
                errors.append(f"{card.id}: domains 为空")
            for d in card.domains:
                domain_card = self.cards.get(d)
                if domain_card is None:
                    errors.append(f"{card.id}: 领域 {d} 不存在")
                elif domain_card.type != CardType.DOMAIN:
                    errors.append(f"{card.id}: {d} 不是 domain 卡片")
            for rel in card.relations:
                if rel.target not in self.cards:
                    errors.append(f"{card.id}: 关系指向不存在的卡片 {rel.target}")
                if rel.type == RelationType.INVOLVES and card.type != CardType.CONFLICT:
                    errors.append(f"{card.id}: involves 只能用于 conflict 卡片")
            if card.lifecycle.value == "superseded" and not card.superseded_by:
                errors.append(f"{card.id}: lifecycle=superseded 时必须提供 superseded_by")
            if card.theory_status and card.type.value not in ("claim", "model"):
                errors.append(f"{card.id}: theory_status 只能用于 claim/model")
            if len(card.sources) > 12:
                warnings.append(f"{card.id}: sources 数量 {len(card.sources)} 超过建议值 12")
            if len(card.relations) > 12:
                warnings.append(f"{card.id}: relations 数量 {len(card.relations)} 超过建议值 12")
            if len(card.body or "") > 4000:
                warnings.append(
                    f"{card.id}: 正文 {len(card.body)} 字超过建议值 4000"
                    "（疑似章级百科：enrich 应改写机制段，而非文末叠加；考虑拆分或留给 construct）"
                )
            # 正文幽灵链接
            for m in WIKILINK_RE.finditer(card.body or ""):
                target = m.group(1).strip()
                if target and target not in self.cards:
                    errors.append(f"{card.id}: 正文幽灵链接 [[{target}]]")
        return errors, warnings
