"""digest / construct 的轻量上下文组装：目录常驻、全文按需、硬上限。"""

from __future__ import annotations

import re
from pathlib import Path

from nexogenesis.ingest import count_chars
from nexogenesis.store import Store
from nexogenesis.yaml_utils import split_frontmatter


DEFAULT_WAVE_BUFFERS = 8
DEFAULT_DEEP_CARDS = 6
DEFAULT_LENS_BUFFERS = 6
DEFAULT_LENS_CARDS = 8

ROLE_PRIORITY = {
    "tension": 0,
    "meaning-unit": 1,
    "link-hypothesis": 2,
    "artifact-table": 3,
    "artifact-figure": 4,
    "evidence": 5,
    "detail": 6,
    "profile-seed": 7,
}

BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")


def card_catalog(store: Store) -> list[dict]:
    """全部卡片一行摘要（无正文）。"""
    rows = []
    for cid, c in sorted(store.cards.items()):
        rows.append({
            "id": c.id,
            "title": c.title,
            "type": c.type.value,
            "domains": list(c.domains),
            "relations": [
                {"target": r.target, "type": r.type.value, "note": r.note} for r in c.relations
            ],
            "line": (
                f"- {c.id} ({c.type.value}) {c.title} "
                f"domains={list(c.domains)} "
                f"relations={[r.target for r in c.relations]}"
            ),
        })
    return rows


def load_buffer_records(paths: list[Path], root: Path) -> list[dict]:
    out = []
    for p in paths:
        try:
            rel = p.relative_to(root).as_posix()
        except ValueError:
            rel = str(p)
        text = p.read_text(encoding="utf-8")
        meta, body = split_frontmatter(text)
        meta = meta or {}
        role = meta.get("role") or p.parent.name
        out.append({
            "path": rel,
            "abs_path": p,
            "text": text,
            "title": str(meta.get("title") or p.stem),
            "role": str(role),
            "status": str(meta.get("status") or ""),
            "source": str(meta.get("source") or ""),
            "proposed_domains": list(meta.get("proposed_domains") or [])
            if isinstance(meta.get("proposed_domains"), list)
            else [],
            "proposed_card_type": meta.get("proposed_card_type"),
            "char_count": count_chars(text),
            "body": body or "",
        })
    return out


def buffer_index_lines(records: list[dict]) -> list[str]:
    lines = []
    for b in records:
        lines.append(
            f"- [{b['status'] or '?'}] {b['role']} | {b['title']} | {b['path']} | source={b['source']}"
        )
    return lines


def select_digest_buffer_wave(
    records: list[dict],
    *,
    max_buffers: int = DEFAULT_WAVE_BUFFERS,
    all_scratch: bool = False,
) -> tuple[list[dict], list[dict]]:
    """选择本波 Buffer；返回 (selected, deferred)。"""
    ordered = sorted(
        records,
        key=lambda b: (
            ROLE_PRIORITY.get(b["role"], 99),
            b["path"],
        ),
    )
    if all_scratch or max_buffers <= 0 or len(ordered) <= max_buffers:
        return ordered, []

    # 优先同 source 成波：取优先级最高的一条的 source，尽量带齐同 source
    seed = ordered[0]
    seed_source = seed["source"]
    same = [b for b in ordered if b["source"] == seed_source] if seed_source else [seed]
    rest = [b for b in ordered if b not in same]

    selected: list[dict] = []
    for b in same + rest:
        if len(selected) >= max_buffers:
            break
        selected.append(b)
    selected_set = {b["path"] for b in selected}
    deferred = [b for b in ordered if b["path"] not in selected_set]
    return selected, deferred


def _tokens_from_buffers(buffers: list[dict]) -> set[str]:
    tokens: set[str] = set()
    for b in buffers:
        for d in b.get("proposed_domains") or []:
            if isinstance(d, str) and d.strip():
                tokens.add(d.strip())
        for m in BOLD_RE.finditer(b.get("text") or ""):
            t = m.group(1).strip()
            if len(t) >= 2:
                tokens.add(t)
        title = b.get("title") or ""
        for part in re.split(r"[\s\-_/：:，,。]+", title):
            if len(part) >= 2:
                tokens.add(part)
    return tokens


def _card_deep_row(c) -> dict:
    return {
        "id": c.id,
        "title": c.title,
        "type": c.type.value,
        "domains": list(c.domains),
        "relations": [
            {"target": r.target, "type": r.type.value, "note": r.note} for r in c.relations
        ],
        "body": c.body or "",
    }


def pin_domain_skeleton(store: Store, cards: list[dict], *, max_deep: int) -> list[dict]:
    """v3.1 风格：深读工作集优先保住相关 domain 骨架，再填实例。"""
    if max_deep <= 0:
        return []
    ordered: list[dict] = []
    seen: set[str] = set()

    def _add(row: dict) -> None:
        cid = row.get("id")
        if not cid or cid in seen:
            return
        seen.add(cid)
        ordered.append(row)

    for row in cards:
        if row.get("type") == "domain":
            _add(row)
    for row in cards:
        for d in row.get("domains") or []:
            if d in seen:
                continue
            c = store.cards.get(d)
            if c and c.type.value == "domain":
                _add(_card_deep_row(c))
    for row in cards:
        _add(row)
    # 仍空席时补全库 domain（截断）
    if len(ordered) < max_deep:
        for cid, c in sorted(store.cards.items()):
            if c.type.value == "domain":
                _add(_card_deep_row(c))
            if len(ordered) >= max_deep:
                break
    return ordered[:max_deep]


def select_deep_cards(
    store: Store,
    buffers: list[dict],
    *,
    max_deep: int = DEFAULT_DEEP_CARDS,
    root: Path | None = None,
    use_graph: bool = True,
) -> list[dict]:
    """选相关卡片注入正文；优先图检索，失败则启发式；始终 pin domain 骨架。"""
    if max_deep <= 0 or not store.cards:
        return []

    raw: list[dict] = []
    if root is not None and use_graph:
        try:
            from nexogenesis.retrieve.context_package import deep_cards_from_graph

            graph_cards = deep_cards_from_graph(root, buffers, max_deep=max_deep)
            if graph_cards:
                raw = graph_cards
        except Exception:
            pass

    if not raw:
        tokens = _tokens_from_buffers(buffers)
        scored: list[tuple[int, str]] = []
        for cid, c in store.cards.items():
            score = 0
            if c.type.value == "domain":
                score += 4
            for d in c.domains:
                if d in tokens:
                    score += 5
            if c.id in tokens or c.title in tokens:
                score += 6
            for t in tokens:
                if t in c.id or t in c.title or t in (c.body or "")[:800]:
                    score += 1
            if score > 0:
                scored.append((score, cid))

        scored.sort(key=lambda x: (-x[0], x[1]))
        if not scored:
            domains = [cid for cid, c in store.cards.items() if c.type.value == "domain"]
            pick = domains[:max_deep]
        else:
            pick = [cid for _, cid in scored[:max_deep]]
        raw = [_card_deep_row(store.cards[cid]) for cid in pick]

    return pin_domain_skeleton(store, raw, max_deep=max_deep)


def load_cards_by_ids(store: Store, ids: list[str]) -> list[dict]:
    out = []
    for cid in ids:
        c = store.cards.get(cid)
        if not c:
            continue
        out.append({
            "id": c.id,
            "title": c.title,
            "type": c.type.value,
            "domains": list(c.domains),
            "relations": [
                {"target": r.target, "type": r.type.value, "note": r.note} for r in c.relations
            ],
            "body": c.body or "",
        })
    return out


def estimate_pack_chars(
    *,
    catalog_lines: list[str],
    deep_cards: list[dict],
    buffers: list[dict],
    extra: str = "",
) -> int:
    total = count_chars(extra)
    total += sum(count_chars(x) for x in catalog_lines)
    for c in deep_cards:
        total += count_chars(c.get("body") or "") + count_chars(c.get("title") or "")
    for b in buffers:
        total += int(b.get("char_count") or count_chars(b.get("text") or ""))
    return total


def read_index_excerpt(root: Path, name: str, max_chars: int = 1500) -> str:
    path = root / "01-Cards" / "_meta" / name
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    if count_chars(text) <= max_chars:
        return text
    # 粗截断按行
    lines = text.splitlines()
    out = []
    cost = 0
    for ln in lines:
        c = count_chars(ln)
        if cost + c > max_chars:
            break
        out.append(ln)
        cost += c
    return "\n".join(out) + "\n\n…（索引已截断）\n"
