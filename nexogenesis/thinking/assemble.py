"""Working Set：双账户（core / conflict / expansion）组装。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nexogenesis.graph.build import load_snapshot, rebuild_graph
from nexogenesis.graph.retrieve import excerpt_body, pick_seeds, tokenize
from nexogenesis.graph.traverse import expand_subgraph
from nexogenesis.models import CardType, RelationType
from nexogenesis.rag.search import rag_search, rag_search_for_cards
from nexogenesis.store import Store
from nexogenesis.thinking.config import (
    get_nested,
    load_attention_config,
    resolve_effective_config,
    validate_attention_config,
)
from nexogenesis.thinking.stm import STMStore


def assemble_working_set(
    root: Path,
    *,
    query: str = "",
    mode: str = "talk",
    seeds: list[str] | None = None,
    buffer_tokens: set[str] | None = None,
    use_stm: bool = True,
    use_graph: bool = True,
    use_rag: bool = True,
    session_overrides: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    raw_cfg = config if config is not None else load_attention_config(root)
    errors, warnings = validate_attention_config(raw_cfg)

    stm_ctx: dict[str, Any] = {}
    overrides = dict(session_overrides or {})
    if use_stm:
        stm = STMStore(root, config=raw_cfg)
        stm_ctx = stm.attention_context()
        slots = stm_ctx.get("slots") or {}
        overrides = {**(slots.get("session_overrides") or {}), **overrides}

    effective = resolve_effective_config(
        raw_cfg, profile=mode if mode in ("talk", "answer", "judge", "digest") else None,
        session_overrides=overrides,
    )
    # construct 等模式仍可用 talk 槽位默认
    if mode == "construct":
        effective = resolve_effective_config(
            raw_cfg, profile="talk", session_overrides=overrides
        )
        effective["resolved_profile"] = "construct"

    budget_chars = int(get_nested(effective, "budget", "chars", default=16000))
    slots_cfg = effective.get("slots") or {}
    n_core = int(slots_cfg.get("core", 3))
    n_expansion = int(slots_cfg.get("expansion", 6))
    n_conflict = int(slots_cfg.get("conflict", 2))
    card_cap = int(get_nested(effective, "budget", "card_slots", default=12))
    total_card_budget = min(card_cap, n_core + n_expansion + n_conflict)

    hops = int(get_nested(effective, "graph", "hops", default=2))
    weak_ties = bool(
        get_nested(effective, "graph", "expansion_prefer_weak_ties", default=True)
    )
    prefer_bridge = bool(
        get_nested(effective, "graph", "prefer_bridge_nodes", default=True)
    )

    stm_tokens = tokenize(stm_ctx.get("focus_tokens") or "")
    all_tokens = set(buffer_tokens or set()) | stm_tokens | tokenize(query)
    cited = list(stm_ctx.get("all_cited") or [])
    tensions = list(stm_ctx.get("all_tensions") or [])
    bridge_hints = list((stm_ctx.get("slots") or {}).get("bridge_hints") or [])

    explicit_seeds = list(seeds or [])
    for cid in cited[:6] + bridge_hints[:4]:
        if cid not in explicit_seeds:
            explicit_seeds.append(cid)

    blind_spots: list[str] = list(warnings)
    for e in errors:
        blind_spots.append(f"attention 配置错误: {e}")

    structure: dict[str, Any] = {
        "status": "ok",
        "seeds": [],
        "nodes": [],
        "edges": [],
        "accounts": {"core": [], "conflict": [], "expansion": []},
    }

    store = Store(root / "01-Cards").load()
    if not use_graph:
        structure["status"] = "skipped"
        blind_spots.append("图检索已禁用（--no-graph）。")
    elif not store.cards:
        structure["status"] = "empty-graph"
        blind_spots.append("图尚无节点；请先 digest 或 capture 写入卡片。")
    else:
        snapshot = load_snapshot(root) or rebuild_graph(root)
        seed_ids = pick_seeds(
            store,
            query=query,
            explicit=explicit_seeds,
            buffer_tokens=all_tokens,
        )
        structure["seeds"] = seed_ids

        max_nodes = max(total_card_budget * 3, 24)
        visited = expand_subgraph(
            store, snapshot, seed_ids, max_hops=hops, max_nodes=max_nodes
        )
        if not visited:
            visited = {
                sid: {"hop": 0, "via": None} for sid in seed_ids if sid in store.cards
            }

        bridge_ids: set[str] = set()
        if prefer_bridge:
            try:
                from nexogenesis.graph.analyze import find_bridge_nodes

                bridge_ids = set(find_bridge_nodes(store, snapshot)[:20])
            except Exception:
                bridge_ids = set()

        ranked = _dual_account_select(
            store,
            visited,
            seed_ids=seed_ids,
            cited=set(cited),
            tensions=tensions,
            query=query,
            tokens=all_tokens,
            bridge_ids=bridge_ids,
            weak_ties=weak_ties,
            weights=effective.get("weights") or {},
            n_core=n_core,
            n_conflict=n_conflict,
            n_expansion=n_expansion,
            total_cap=total_card_budget,
        )

        included: set[str] = set()
        used_chars = 0
        half = budget_chars // 2
        nodes_out: list[dict[str, Any]] = []
        accounts_out = {"core": [], "conflict": [], "expansion": []}

        for account, nid in ranked:
            if len(nodes_out) >= total_card_budget:
                break
            c = store.cards[nid]
            excerpt = excerpt_body(c.body, 800)
            cost = len(excerpt) + len(c.title)
            if used_chars + cost > half and nodes_out:
                break
            used_chars += cost
            included.add(nid)
            node = {
                "id": c.id,
                "title": c.title,
                "type": c.type.value,
                "domains": list(c.domains),
                "origin": c.origin.value,
                "hop": visited.get(nid, {}).get("hop", 0),
                "via": visited.get(nid, {}).get("via"),
                "account": account,
                "excerpt": excerpt,
            }
            nodes_out.append(node)
            accounts_out[account].append(nid)

        edges_out = []
        for e in snapshot.edges:
            if e.from_id in included and e.to_id in included:
                edges_out.append({
                    "from": e.from_id,
                    "to": e.to_id,
                    "kind": e.kind,
                    "type": e.relation_type,
                })

        structure.update({
            "status": "ok",
            "nodes": nodes_out,
            "edges": edges_out,
            "accounts": accounts_out,
            "budget": {"chars": used_chars, "structure_nodes": len(nodes_out)},
        })
        if not nodes_out:
            blind_spots.append("种子未扩展出节点；可显式 --seed 或扩大语料。")

    # RAG 工具书
    material: list[dict[str, Any]] = []
    rag_enabled = use_rag and bool(get_nested(effective, "rag", "enabled", default=True))
    rag_top = int(
        get_nested(effective, "budget", "rag_chunks", default=6)
        or get_nested(effective, "rag", "max_chunks", default=6)
    )
    kinds = effective.get("rag_kinds")
    if not kinds:
        from nexogenesis.retrieve.context_package import MODE_RAG_KINDS

        kinds = MODE_RAG_KINDS.get(mode, MODE_RAG_KINDS["talk"])

    if rag_enabled:
        hits = rag_search(root, query or (stm_ctx.get("focus_tokens") or ""), kinds=kinds, top=rag_top)
        card_ids = [n["id"] for n in structure.get("nodes") or []]
        if card_ids:
            linked_hits = rag_search_for_cards(root, card_ids[:6], top_per_card=2)
            seen = {h["chunk_id"] for h in hits}
            for h in linked_hits:
                if h["chunk_id"] not in seen:
                    hits.append(h)
                    seen.add(h["chunk_id"])

        rag_budget = budget_chars // 2
        used = 0
        for h in hits:
            cost = len(h.get("excerpt") or "")
            if used + cost > rag_budget and material:
                break
            used += cost
            material.append({
                "chunk_id": h["chunk_id"],
                "kind": h["kind"],
                "attribution": h["attribution"],
                "anchor": h["anchor"],
                "excerpt": h["excerpt"],
                "linked_cards": h.get("linked_cards") or [],
            })
        if not hits and (query.strip() or stm_ctx.get("focus_tokens")):
            blind_spots.append("RAG 无命中；可运行 rag index 或扩充语料。")
    else:
        if not use_rag:
            blind_spots.append("RAG 已禁用（--no-rag）。")
        else:
            blind_spots.append("RAG 已在 attention 配置中关闭。")

    status = structure.get("status", "ok")
    if status == "ok" and not structure.get("nodes") and not material:
        status = "empty"

    pkg = {
        "query": query,
        "mode": mode,
        "status": status,
        "structure": {
            "seeds": structure.get("seeds") or [],
            "nodes": structure.get("nodes") or [],
            "edges": structure.get("edges") or [],
            "accounts": structure.get("accounts") or {},
        },
        "material": material,
        "stm": {
            "session_id": stm_ctx.get("current_session_id"),
            "focus": (stm_ctx.get("slots") or {}).get("focus") or "",
            "tensions": (stm_ctx.get("slots") or {}).get("tensions") or [],
            "cited_cards": (stm_ctx.get("slots") or {}).get("cited_cards") or [],
            "user_directives": (stm_ctx.get("slots") or {}).get("user_directives") or [],
            "recent_sessions": [
                {"id": r["id"], "title": r.get("title"), "focus": r.get("focus")}
                for r in (stm_ctx.get("recent_sessions") or [])[:5]
            ],
        },
        "attention": {
            "profile": effective.get("resolved_profile"),
            "slots": {
                "core": n_core,
                "expansion": n_expansion,
                "conflict": n_conflict,
            },
            "session_overrides": overrides or {},
        },
        "blind_spots": blind_spots,
        "budget": {
            "chars": sum(len(n.get("excerpt") or "") for n in structure.get("nodes") or [])
            + sum(len(m.get("excerpt") or "") for m in material),
            "structure_nodes": len(structure.get("nodes") or []),
            "rag_chunks": len(material),
        },
    }
    return pkg


def _dual_account_select(
    store: Store,
    visited: dict[str, dict],
    *,
    seed_ids: list[str],
    cited: set[str],
    tensions: list[str],
    query: str,
    tokens: set[str],
    bridge_ids: set[str],
    weak_ties: bool,
    weights: dict[str, Any],
    n_core: int,
    n_conflict: int,
    n_expansion: int,
    total_cap: int,
) -> list[tuple[str, str]]:
    """返回 [(account, card_id), ...] 有序名单。"""
    w_exp = weights.get("expansion") or {}
    w_conf = weights.get("conflict") or {}
    tension_blob = " ".join(tensions)
    tension_toks = tokenize(tension_blob)
    q_toks = tokenize(query) | tokens

    selected: list[tuple[str, str]] = []
    used: set[str] = set()

    # core：种子 + 已引用
    core_cands: list[str] = []
    for sid in seed_ids:
        if sid in visited and sid not in core_cands:
            core_cands.append(sid)
    for cid in cited:
        if cid in visited and cid not in core_cands:
            core_cands.append(cid)
    for cid in core_cands:
        if len([a for a, _ in selected if a == "core"]) >= n_core:
            break
        if cid not in used and cid in store.cards:
            selected.append(("core", cid))
            used.add(cid)

    # conflict 保底
    conflict_scored: list[tuple[float, str]] = []
    for nid in visited:
        if nid in used or nid not in store.cards:
            continue
        c = store.cards[nid]
        score = 0.0
        rel = _relevance(c, q_toks)
        score += float(w_conf.get("relevance", 0.4)) * rel
        if c.type == CardType.CONFLICT:
            score += float(w_conf.get("conflicts_edge", 0.25)) * 2
        has_conflict_edge = any(
            r.type == RelationType.CONFLICTS_WITH for r in c.relations
        ) or any(
            r.type == RelationType.INVOLVES for r in c.relations
        )
        if has_conflict_edge:
            score += float(w_conf.get("conflicts_edge", 0.25))
        hay = f"{c.id} {c.title} {(c.body or '')[:400]}"
        if tension_toks and any(t in hay for t in tension_toks):
            score += float(w_conf.get("tension_match", 0.35)) * 2
        if score > 0.05:
            conflict_scored.append((score, nid))
    conflict_scored.sort(key=lambda x: (-x[0], x[1]))
    for _, nid in conflict_scored:
        if len([a for a, _ in selected if a == "conflict"]) >= n_conflict:
            break
        if len(selected) >= total_cap:
            break
        selected.append(("conflict", nid))
        used.add(nid)

    # expansion
    exp_scored: list[tuple[float, str]] = []
    for nid in visited:
        if nid in used or nid not in store.cards:
            continue
        c = store.cards[nid]
        hop = int(visited[nid].get("hop") or 0)
        rel = _relevance(c, q_toks)
        novelty = 0.0
        if nid not in cited:
            novelty += 1.0
        if hop >= 2 and weak_ties:
            novelty += 0.5
        if nid in bridge_ids:
            novelty += 0.8
        penalty = 1.0 if nid in cited else 0.0
        score = (
            float(w_exp.get("relevance", 0.55)) * rel
            + float(w_exp.get("novelty", 0.35)) * novelty
            - float(w_exp.get("already_cited_penalty", 0.4)) * penalty
        )
        exp_scored.append((score, nid))
    exp_scored.sort(key=lambda x: (-x[0], x[1]))
    for _, nid in exp_scored:
        if len([a for a, _ in selected if a == "expansion"]) >= n_expansion:
            break
        if len(selected) >= total_cap:
            break
        selected.append(("expansion", nid))
        used.add(nid)

    return selected


def _relevance(card, tokens: set[str]) -> float:
    if not tokens:
        return 0.1
    hay = f"{card.id} {card.title} {(card.body or '')[:500]}"
    hits = sum(1 for t in tokens if t in hay)
    return min(1.0, hits / max(3, min(8, len(tokens))))
