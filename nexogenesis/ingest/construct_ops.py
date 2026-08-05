"""construct 可执行结构动作：确定性补边 + ops 草稿（不只空谈）。"""

from __future__ import annotations

import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from nexogenesis.models import CardType, Lifecycle, RelationType
from nexogenesis.store import Store
from nexogenesis.yaml_utils import atomic_write_file

_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]{2,}", re.UNICODE)
_CJK_RUN = re.compile(r"[\u4e00-\u9fff]{2,}")
_STOP = {
    "与", "的", "和", "或", "及", "在", "对", "之", "及其", "以及",
    "是否", "如何", "什么", "一个", "一种", "可以", "应当", "必须",
    "conflict", "claim", "model", "domain", "vs", "versus",
    # 停用词级噪声：高频但无枢纽语义（复盘：经济/市场/之争/政策曾淹没候选列表）
    "经济", "市场", "政策", "之争", "收入", "成本",
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
    """conflict 缺 involves → 需 LLM 填双方 claim/model 的 ops。

    不再给「同域热门卡」候选（复盘：同域共现 ≠ 同争议，候选有害）；
    改为要求从 conflict 正文抽对立双方，无匹配则新建两造 claim。
    superseded/archived 的 conflict 不报（假待办）。
    """
    ops: list[dict[str, Any]] = []
    for cid, c in sorted(store.cards.items()):
        if c.type != CardType.CONFLICT:
            continue
        if c.lifecycle != Lifecycle.ACTIVE:
            continue
        involves = [r for r in c.relations if r.type == RelationType.INVOLVES]
        if involves:
            continue
        ops.append({
            "op": "require_involves",
            "reason": (
                "conflict 缺 involves：从正文/sources 抽出对立双方；"
                "匹配到现有 claim/model 则改挂，无合适对象则新建两造 claim 再 involves"
                "（结构必需，不算第二次消化）"
            ),
            "cards": [cid],
            "lens": "distinguish",
        })
    return ops


def build_involves_semantic_ops(store: Store) -> list[dict[str, Any]]:
    """conflict 有 involves 但挂错类型/数量异常 → 语义修正 ops（数量闸门 ≠ 语义闸门）。"""
    ops: list[dict[str, Any]] = []
    for cid, c in sorted(store.cards.items()):
        if c.type != CardType.CONFLICT:
            continue
        if c.lifecycle != Lifecycle.ACTIVE:
            continue
        involves = [r for r in c.relations if r.type == RelationType.INVOLVES]
        if not involves:
            continue
        bad = [
            r.target
            for r in involves
            if r.target in store.cards
            and store.cards[r.target].type not in (CardType.CLAIM, CardType.MODEL)
        ]
        if bad:
            ops.append({
                "op": "fix_involves_semantics",
                "reason": (
                    "involves 指向非 claim/model："
                    + ", ".join(bad)
                    + "；应改挂对立双方 claim/model（缺两造时允许破例新建两造 claim）"
                ),
                "cards": [cid] + bad,
                "lens": "distinguish",
            })
        elif not (2 <= len(involves) <= 4):
            ops.append({
                "op": "fix_involves_count",
                "reason": (
                    f"involves 数={len(involves)}（建议 2–4）："
                    "过少不像两造，过多像枢纽，考虑收窄或拆分"
                ),
                "cards": [cid],
                "lens": "distinguish",
            })
    return ops


def find_overloaded_domains(
    store: Store,
    *,
    max_members: int = 25,
    max_relations: int = 12,
    max_body: int = 3000,
) -> list[dict[str, Any]]:
    """挂靠过多 / 边过多 / 正文过长的 domain → domain_overloaded（cluster 应优先）。"""
    out: list[dict[str, Any]] = []
    for cid, c in sorted(store.cards.items()):
        if c.type != CardType.DOMAIN:
            continue
        members = [x for x in store.by_domain.get(cid, []) if x != cid]
        n_rel = len(c.relations or [])
        n_body = len(c.body or "")
        if len(members) > max_members or n_rel > max_relations or n_body > max_body:
            out.append({
                "id": cid,
                "members": len(members),
                "relations": n_rel,
                "body_chars": n_body,
            })
    return out


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
            # 已是某张卡 id 的子串 → 概念已被更长名的卡覆盖，抑制
            if any(term in cid for cid in store.cards):
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
    involves_ops = build_involves_stub_ops(store) + build_involves_semantic_ops(store)
    hub_ops = find_hub_term_candidates(store)
    overloaded = find_overloaded_domains(store)
    return {
        "seed_link_writes": seed_writes,
        "ops_need_llm": involves_ops + hub_ops,
        "stats": {
            "seed_link_count": len(seed_writes),
            "require_involves_count": len(involves_ops),
            "hub_candidate_count": len(hub_ops),
            "overloaded_domains": overloaded,
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

    overloaded = plan["stats"].get("overloaded_domains") or []
    n_seeds = plan["stats"]["seed_link_count"]
    n_involves = plan["stats"]["require_involves_count"]
    n_hubs = plan["stats"]["hub_candidate_count"]
    # 动态顺序：按真实债务置顶；无债务的镜头不出现在顺序里（假待办与错候选一样消耗信任）
    priority: list[str] = []
    step = 1
    if overloaded:
        names = "、".join(f"`{d['id']}`" for d in overloaded[:5])
        priority.append(
            f"{step}. cluster 优先：domain 过载 {names}——分裂 sibling domain 并重挂实例"
        )
        step += 1
    if n_seeds:
        priority.append(
            f"{step}. 先 construct --apply-seed-links（{n_seeds} 张空边；重挂/新建后常见，有数量时置顶）"
        )
        step += 1
    if n_involves:
        priority.append(
            f"{step}. distinguish：处理 require_involves / fix_involves_semantics（{n_involves} 项）"
        )
        step += 1
    if n_hubs:
        priority.append(
            f"{step}. articulate：处理 suggest_entity_hub（{n_hubs} 个候选；默认只读，入 batch 前须筛选）"
        )
        step += 1
    tail = "按需 cross_source" if overloaded else "按需 cluster / cross_source"
    priority.append(f"{step}. {tail}；无债务的镜头直接跳过，勿当完成态")

    llm_path = out_dir / "structure-ops-llm.yaml"
    llm_doc = {
        "note": "以下 ops 不能直接 apply；请按 lens 生成完整 write --batch（batch.yaml）",
        "priority": priority,
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
        f"- involves 问题（缺失/语义错配）的 conflict：**{plan['stats']['require_involves_count']}** 张",
        f"- 枢纽概念候选（升格 entity/model）：**{plan['stats']['hub_candidate_count']}** 个（默认只读，入 batch 前须筛选）",
        f"- 图分析其它 ops：{len(graph_ops)}",
    ]
    if overloaded:
        lines.append(
            f"- ⚠ domain 过载：**{len(overloaded)}** 张——"
            + "、".join(
                f"`{d['id']}`(挂靠={d['members']},边={d['relations']})" for d in overloaded[:5]
            )
            + "；cluster 应优先"
        )
    lines += [
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

    lines.extend(["", "## 1. distinguish：conflict 必须 involves（存在性 + 语义合法性）", ""])
    for op in plan["ops_need_llm"]:
        if op.get("op") == "require_involves":
            lines.append(f"- `{op['cards'][0]}`：{op.get('reason')}")
        elif op.get("op") in ("fix_involves_semantics", "fix_involves_count"):
            lines.append(f"- `{op['cards'][0]}`：{op.get('reason')}")
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
        lines.append("- （过滤后无候选——本轮建议跳过 articulate 镜头）")

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
        *priority,
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
