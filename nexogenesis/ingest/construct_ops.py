"""construct 可执行结构动作：确定性补边 + ops 草稿（不只空谈）。"""

from __future__ import annotations

import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from nexogenesis.models import CardType, RelationType
from nexogenesis.store import Store
from nexogenesis.yaml_utils import atomic_write_file

_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]{2,}", re.UNICODE)
_CJK_RUN = re.compile(r"[\u4e00-\u9fff]{2,}")
_STOP = {
    "与", "的", "和", "或", "及", "在", "对", "之", "及其", "以及",
    "是否", "如何", "什么", "一个", "一种", "可以", "应当", "必须",
    "conflict", "claim", "model", "domain", "vs", "versus",
}


def _terms_from_text(text: str) -> list[str]:
    """英文/数字 token + 连续汉字的 2–4 字 n-gram（便于无空格中文标题抽枢纽）。"""
    out: list[str] = []
    for tok in _TOKEN_RE.findall(text):
        if tok in _STOP or tok.isdigit() or len(tok) < 2 or len(tok) > 24:
            continue
        out.append(tok)
    for run in _CJK_RUN.findall(text):
        for n in range(2, min(5, len(run) + 1)):
            for i in range(len(run) - n + 1):
                gram = run[i : i + n]
                if gram not in _STOP:
                    out.append(gram)
    return out


def build_seed_link_writes(store: Store, *, today: str | None = None) -> list[dict[str, Any]]:
    """
    确定性补边：非 domain 且无 outgoing relations 时，
    对其有效 domain 补 applies-to（已有同边则跳过）。
    写出完整 card write（保留正文），可直接 write --batch。
    """
    today = today or date.today().isoformat()
    writes: list[dict[str, Any]] = []
    domain_ids = {cid for cid, c in store.cards.items() if c.type == CardType.DOMAIN}

    for cid, c in sorted(store.cards.items()):
        if c.type == CardType.DOMAIN:
            continue
        if c.lifecycle.value == "archived":
            continue
        # 仅空 relations：已有边留给镜头语义补全，避免覆盖人工结构
        if c.relations:
            continue
        new_rels: list[dict[str, Any]] = []
        for d in c.domains:
            if d not in domain_ids:
                continue
            new_rels.append({
                "target": d,
                "type": "applies-to",
                "note": "construct seed-link：挂回领域（确定性补边）",
            })
        if not new_rels:
            continue
        writes.append(_card_write_from_existing(c, new_rels, today=today))
    return writes


def build_involves_stub_ops(store: Store) -> list[dict[str, Any]]:
    """conflict 缺 involves → 需 LLM 填双方 claim/model 的 ops。"""
    ops: list[dict[str, Any]] = []
    for cid, c in sorted(store.cards.items()):
        if c.type != CardType.CONFLICT:
            continue
        involves = [r for r in c.relations if r.type == RelationType.INVOLVES]
        if involves:
            continue
        members = [
            m
            for d in c.domains
            for m in store.by_domain.get(d, [])
            if m != cid and m in store.cards and store.cards[m].type in (
                CardType.CLAIM, CardType.MODEL
            )
        ]
        ops.append({
            "op": "require_involves",
            "reason": "conflict 缺 involves；须指向对立双方 claim/model，勿只用 applies-to domain",
            "cards": [cid],
            "candidate_members": members[:12],
            "lens": "distinguish",
        })
    return ops


def find_hub_term_candidates(
    store: Store,
    *,
    min_count: int = 3,
    max_hubs: int = 12,
) -> list[dict[str, Any]]:
    """
    同 domain 内标题高频词，且尚无同名 entity/model 卡 → 枢纽概念候选。
    不自动建卡，只提案供 articulate 镜头处理。
    """
    by_domain: dict[str, list[str]] = {}
    for cid, c in store.cards.items():
        if c.type == CardType.DOMAIN:
            continue
        for d in c.domains:
            by_domain.setdefault(d, []).append(cid)

    ops: list[dict[str, Any]] = []
    seen_terms: set[str] = set()
    for domain, members in sorted(by_domain.items()):
        if len(members) < min_count:
            continue
        counter: Counter[str] = Counter()
        term_cards: dict[str, list[str]] = {}
        for mid in members:
            c = store.cards[mid]
            text = f"{c.id} {c.title}"
            for tok in _terms_from_text(text):
                counter[tok] += 1
                term_cards.setdefault(tok, []).append(mid)
        # 优先较长术语（同频时）
        ranked = sorted(
            counter.items(),
            key=lambda kv: (-kv[1], -len(kv[0]), kv[0]),
        )
        for term, cnt in ranked:
            if cnt < min_count:
                continue
            if term in seen_terms:
                continue
            if term in store.cards:
                continue
            cards = uniq(term_cards.get(term) or [])
            if len(cards) < min_count:
                continue
            # 若已被更长术语覆盖同一批卡，跳过短词
            if any(
                term != t and term in t and set(cards).issubset(set(term_cards.get(t) or []))
                for t in seen_terms
            ):
                continue
            seen_terms.add(term)
            ops.append({
                "op": "suggest_entity_hub",
                "reason": (
                    f"领域 `{domain}` 内「{term}」出现在 {len(cards)} 张卡标题/id 中；"
                    "可升格为 entity（定义对象）或补强已有 model，并让相关卡 based-on/involves 指过去——"
                    "不是新建第八种「概念」类型"
                ),
                "cards": cards[:8],
                "term": term,
                "domain": domain,
                "lens": "articulate",
            })
            if len(ops) >= max_hubs:
                return ops
    return ops


def build_structure_action_plan(store: Store) -> dict[str, Any]:
    """汇总确定性动作 + 需 LLM 的 ops。"""
    seed_writes = build_seed_link_writes(store)
    involves_ops = build_involves_stub_ops(store)
    hub_ops = find_hub_term_candidates(store)
    return {
        "seed_link_writes": seed_writes,
        "ops_need_llm": involves_ops + hub_ops,
        "stats": {
            "seed_link_count": len(seed_writes),
            "require_involves_count": len(involves_ops),
            "hub_candidate_count": len(hub_ops),
        },
    }


def write_construct_action_artifacts(
    root: Path,
    store: Store,
    *,
    existing_graph_ops: list[dict[str, Any]] | None = None,
) -> dict[str, Path]:
    """
    写入：
    - structure-seed-links.yaml（可直接 --apply-seed-links）
    - structure-ops-draft.md（给人/Agent 看的完整行动单）
    - structure-ops-llm.yaml（需镜头补全的提案，非完整 write）
    """
    root = root.resolve()
    out_dir = root / ".nexogenesis" / "tmp" / "construct"
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = build_structure_action_plan(store)
    graph_ops = list(existing_graph_ops or [])

    paths: dict[str, Path] = {}

    seed_path = out_dir / "structure-seed-links.yaml"
    seed_doc = {
        "operation": {
            "id": f"construct-seed-links-{date.today().isoformat()}",
            "source": "construct deterministic seed-links",
            "approved_by": "user",
            "note": "确定性补边：空 relations → applies-to 所属 domain。可用 construct --apply-seed-links。",
        },
        "writes": plan["seed_link_writes"],
    }
    atomic_write_file(
        seed_path,
        yaml.safe_dump(seed_doc, allow_unicode=True, sort_keys=False),
    )
    paths["seed_links"] = seed_path

    llm_path = out_dir / "structure-ops-llm.yaml"
    llm_doc = {
        "note": "以下 ops 不能直接 apply；请按 lens 生成完整 write --batch（batch.yaml）",
        "priority": [
            "1. 若 seed-links 非空：先 construct --apply-seed-links（或确认后 write 该 yaml）",
            "2. distinguish：处理 require_involves",
            "3. articulate：处理 suggest_entity_hub 与链接空洞",
            "4. cluster / cross_source：按需",
        ],
        "ops": plan["ops_need_llm"] + graph_ops,
    }
    atomic_write_file(
        llm_path,
        yaml.safe_dump(llm_doc, allow_unicode=True, sort_keys=False),
    )
    paths["ops_llm"] = llm_path

    draft = out_dir / "structure-ops-draft.md"
    lines = [
        "# construct 结构行动单（可执行，非空谈）",
        "",
        f"- 确定性补边（seed-links）：**{plan['stats']['seed_link_count']}** 张",
        f"- 待补 involves 的 conflict：**{plan['stats']['require_involves_count']}** 张",
        f"- 枢纽概念候选（升格 entity/model）：**{plan['stats']['hub_candidate_count']}** 个",
        f"- 图分析其它 ops：{len(graph_ops)}",
        "",
        "## 0. 立刻可做（无需 LLM）",
        "",
    ]
    if plan["seed_link_writes"]:
        lines.append(
            f"运行：`python -m nexogenesis construct --apply-seed-links --root .`  "
            f"或 `write --batch {seed_path.as_posix()}`"
        )
        lines.append("")
        for w in plan["seed_link_writes"][:15]:
            rels = [r for r in w.get("relations") or [] if "seed-link" in (r.get("note") or "")]
            targets = ", ".join(r["target"] for r in rels) or "(merge)"
            lines.append(f"- enrich `{w['id']}` → applies-to {targets}")
        if len(plan["seed_link_writes"]) > 15:
            lines.append(f"- …另有 {len(plan['seed_link_writes']) - 15} 张")
    else:
        lines.append("（无空 relations 可自动挂 domain 的卡）")

    lines.extend(["", "## 1. distinguish：conflict 必须 involves", ""])
    for op in plan["ops_need_llm"]:
        if op.get("op") != "require_involves":
            continue
        cands = ", ".join(f"`{x}`" for x in (op.get("candidate_members") or [])[:6])
        lines.append(
            f"- `{op['cards'][0]}`：补 involves 双方。"
            f" 同域候选：{cands or '（请从目录另选 claim/model）'}"
        )
    if plan["stats"]["require_involves_count"] == 0:
        lines.append("- （无）")

    lines.extend(["", "## 2. articulate：枢纽升格（不是新类型「概念」）", ""])
    for op in plan["ops_need_llm"]:
        if op.get("op") != "suggest_entity_hub":
            continue
        lines.append(
            f"- 术语「**{op.get('term')}**」（domain `{op.get('domain')}`）："
            f"考虑新建 entity 或挂到已有 model；涉及 {', '.join(f'`{c}`' for c in op.get('cards') or [])}"
        )
    if plan["stats"]["hub_candidate_count"] == 0:
        lines.append("- （无高频未升格枢纽）")

    lines.extend(["", "## 3. 图分析遗留", ""])
    if graph_ops:
        for op in graph_ops[:20]:
            lines.append(
                f"- **{op.get('op')}**: {op.get('reason')} → {op.get('cards')}"
            )
    else:
        lines.append("- （无）")

    lines.extend([
        "",
        "## 4. 建议镜头顺序",
        "",
        "1. `construct --apply-seed-links`（若第 0 步有数量）",
        "2. `construct --lens distinguish`",
        "3. `construct --lens articulate`",
        "4. 按需 `cluster` / `cross_source`",
        "",
        f"机器可读：`{llm_path.name}` / `{seed_path.name}`",
        "",
    ])
    atomic_write_file(draft, "\n".join(lines))
    paths["draft"] = draft
    return paths


def merge_action_ops_into_graph_signals(
    ops_need_llm: list[dict[str, Any]],
) -> dict[str, list[str]]:
    signals: dict[str, list[str]] = {
        "cluster": [],
        "distinguish": [],
        "articulate": [],
        "cross_source": [],
    }
    for op in ops_need_llm:
        lens = op.get("lens") or "articulate"
        cards = ", ".join(f"`{c}`" for c in op.get("cards") or [])
        term = op.get("term")
        extra = f" 术语「{term}」" if term else ""
        line = f"[construct-ops] {op.get('op')}: {op.get('reason')}{extra} → {cards}"
        if lens not in signals:
            lens = "articulate"
        if line not in signals[lens]:
            signals[lens].append(line)
    return signals


def _card_write_from_existing(c, relations: list[dict], *, today: str) -> dict[str, Any]:
    return {
        "target": "card",
        "id": c.id,
        "title": c.title,
        "type": c.type.value,
        "maturity": c.maturity.value,
        "lifecycle": c.lifecycle.value,
        "domains": list(c.domains),
        "origin": c.origin.value,
        "sources": list(c.sources),
        "relations": relations,
        "created": c.created,
        "updated": today,
        "body": c.body or "",
        **({"theory_status": c.theory_status.value} if c.theory_status else {}),
        **({"superseded_by": c.superseded_by} if c.superseded_by else {}),
    }


def uniq(xs: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in xs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
