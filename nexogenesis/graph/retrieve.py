from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from nexogenesis.graph.build import load_snapshot, rebuild_graph
from nexogenesis.graph.traverse import expand_subgraph
from nexogenesis.models import CardType
from nexogenesis.store import Store

_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


def tokenize(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text) if len(t) >= 2}


def pick_seeds(
    store: Store,
    *,
    query: str = "",
    explicit: list[str] | None = None,
    buffer_tokens: set[str] | None = None,
) -> list[str]:
    seeds: list[str] = []
    seen: set[str] = set()

    def add(cid: str) -> None:
        if cid in store.cards and cid not in seen:
            seen.add(cid)
            seeds.append(cid)

    for sid in explicit or []:
        add(sid)

    q_tokens = tokenize(query)
    btokens = buffer_tokens or set()

    scored: list[tuple[int, str]] = []
    for cid, card in store.cards.items():
        if card.lifecycle.value == "archived":
            continue
        score = 0
        hay = f"{cid} {card.title} {(card.body or '')[:600]}"
        for t in q_tokens | btokens:
            if t in hay:
                score += 3
        if card.type == CardType.DOMAIN:
            score += 1
        for d in card.domains:
            if d in q_tokens or d in btokens:
                score += 4
        if score > 0:
            scored.append((score, cid))

    scored.sort(key=lambda x: (-x[0], x[1]))
    for _, cid in scored[:8]:
        add(cid)

    if not seeds and scored:
        for _, cid in scored[:3]:
            add(cid)

    if not seeds:
        for cid, card in store.cards.items():
            if card.type == CardType.DOMAIN:
                add(cid)
                if len(seeds) >= 3:
                    break

    return seeds


def rank_nodes(
    store: Store,
    visited: dict[str, dict],
    *,
    query: str = "",
    buffer_tokens: set[str] | None = None,
) -> list[str]:
    q_tokens = tokenize(query)
    btokens = buffer_tokens or set()

    def score_nid(nid: str) -> int:
        c = store.cards[nid]
        s = 0
        hay = f"{nid} {c.title} {(c.body or '')[:500]}"
        for t in q_tokens | btokens:
            if t in hay:
                s += 3
        if c.type == CardType.CONFLICT:
            s += 2
        if c.type == CardType.MODEL:
            s += 1
        hop = visited[nid].get("hop", 0)
        s -= hop
        maturity = c.maturity.value
        if maturity == "mature":
            s += 1
        elif maturity == "growing":
            s += 0
        return s

    ids = list(visited.keys())
    ids.sort(key=lambda x: (-score_nid(x), x))
    return ids


def excerpt_body(body: str, max_chars: int = 800) -> str:
    text = (body or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 20].rstrip() + "\n\n…（摘录截断）"


def graph_retrieve(
    root: Path,
    *,
    query: str = "",
    seeds: list[str] | None = None,
    buffer_tokens: set[str] | None = None,
    max_hops: int = 2,
    max_nodes: int = 24,
    max_chars: int = 12000,
    excerpt_per_card: int = 800,
    rebuild: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    store = Store(root / "01-Cards").load()

    if not store.cards:
        return {
            "status": "empty-graph",
            "query": query,
            "seeds": [],
            "nodes": [],
            "edges": [],
            "blind_spots": ["图尚无节点；请先 digest 或 capture 写入卡片。"],
        }

    snapshot = load_snapshot(root)
    if snapshot is None or rebuild:
        snapshot = rebuild_graph(root)

    small_graph = len(store.cards) < 30
    effective_hops = 1 if small_graph else max_hops
    effective_max = min(max_nodes, len(store.cards)) if small_graph else max_nodes

    seed_ids = pick_seeds(
        store,
        query=query,
        explicit=seeds,
        buffer_tokens=buffer_tokens,
    )

    visited = expand_subgraph(
        store,
        snapshot,
        seed_ids,
        max_hops=effective_hops,
        max_nodes=effective_max,
    )

    if not visited:
        visited = {sid: {"hop": 0, "via": None} for sid in seed_ids if sid in store.cards}

    ranked = rank_nodes(store, visited, query=query, buffer_tokens=buffer_tokens)

    nodes_out: list[dict[str, Any]] = []
    edges_out: list[dict[str, Any]] = []
    used_chars = 0
    included: set[str] = set()

    for nid in ranked:
        if used_chars >= max_chars:
            break
        c = store.cards[nid]
        excerpt = excerpt_body(c.body, excerpt_per_card)
        cost = len(excerpt) + len(c.title)
        if used_chars + cost > max_chars and nodes_out:
            break
        used_chars += cost
        included.add(nid)
        nodes_out.append({
            "id": c.id,
            "title": c.title,
            "type": c.type.value,
            "domains": list(c.domains),
            "origin": c.origin.value,
            "hop": visited[nid]["hop"],
            "via": visited[nid]["via"],
            "excerpt": excerpt,
        })

    for e in snapshot.edges:
        if e.from_id in included and e.to_id in included:
            edges_out.append({
                "from": e.from_id,
                "to": e.to_id,
                "kind": e.kind,
                "type": e.relation_type,
            })

    return {
        "status": "ok",
        "query": query,
        "seeds": seed_ids,
        "nodes": nodes_out,
        "edges": edges_out,
        "blind_spots": [] if nodes_out else ["种子未扩展出节点；可显式 --seed 或扩大语料。"],
        "budget": {"chars": used_chars, "structure_nodes": len(nodes_out)},
    }
