from __future__ import annotations

from collections import deque

from nexogenesis.graph.model import Edge, GraphSnapshot
from nexogenesis.models import CardType, RelationType
from nexogenesis.store import Store


HOP2_RELATIONS = {
    RelationType.SUPPORTS.value,
    RelationType.EXTENDS.value,
    RelationType.APPLIES_TO.value,
    RelationType.BASED_ON.value,
    RelationType.INFLUENCES.value,
    RelationType.EXAMPLE_OF.value,
}


def expand_subgraph(
    store: Store,
    snapshot: GraphSnapshot,
    seeds: list[str],
    *,
    max_hops: int = 2,
    max_nodes: int = 24,
) -> dict[str, dict]:
    """BFS 扩展；返回 node_id -> {hop, via}。"""
    adj = snapshot.adjacency()
    visited: dict[str, dict] = {}
    queue: deque[tuple[str, int, Edge | None]] = deque()

    for sid in seeds:
        if sid in store.cards and sid not in visited:
            queue.append((sid, 0, None))

    while queue and len(visited) < max_nodes:
        nid, hop, via_edge = queue.popleft()
        if nid in visited:
            continue
        via_desc = None
        if via_edge is not None:
            rt = via_edge.relation_type or via_edge.kind
            via_desc = f"{via_edge.kind}:{rt}→{via_edge.to_id}"
        visited[nid] = {"hop": hop, "via": via_desc}

        if hop >= max_hops:
            continue

        card = store.cards.get(nid)
        if card and card.lifecycle.value == "archived":
            continue

        for edge in adj.get(nid, []):
            if edge.to_id not in store.cards:
                continue
            target_card = store.cards[edge.to_id]
            if target_card.lifecycle.value == "archived":
                continue

            next_hop = hop + 1
            if next_hop > max_hops:
                continue

            if hop >= 1:
                if edge.kind == "relation" and edge.relation_type not in HOP2_RELATIONS:
                    if edge.relation_type != RelationType.INVOLVES.value:
                        continue
                if edge.kind not in ("relation", "wikilink", "domain"):
                    continue

            if card and card.type == CardType.CONFLICT:
                if edge.kind == "relation" and edge.relation_type == RelationType.INVOLVES.value:
                    queue.append((edge.to_id, next_hop, edge))
                    continue

            queue.append((edge.to_id, next_hop, edge))

    return visited
