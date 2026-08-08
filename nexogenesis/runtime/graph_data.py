from __future__ import annotations

from pathlib import Path

from nexogenesis.graph.build import load_snapshot, rebuild_graph
from nexogenesis.store import Store


def _primary_domain(domains: list[str]) -> str:
    return domains[0] if domains else "_none"


def _bundle_id(d1: str, d2: str) -> str:
    return d1 if d1 == d2 else "::".join(sorted([d1, d2]))


def build_graph_payload(root: Path) -> dict:
    """从卡片 Store + 图快照构建前端图载荷（不含坐标，坐标由 layout 模块补充）。"""
    root = root.resolve()
    store = Store(root / "01-Cards").load()
    snapshot = load_snapshot(root)
    if snapshot is None:
        snapshot = rebuild_graph(root)

    domain_of: dict[str, str] = {}
    nodes: list[dict] = []
    for cid in sorted(store.cards):
        c = store.cards[cid]
        if c.lifecycle.value != "active":
            continue
        domain_of[cid] = _primary_domain(c.domains)
        nodes.append({
            "id": c.id,
            "title": c.title,
            "type": c.type.value,
            "domains": c.domains,
        })

    node_ids = set(domain_of)
    edges: list[dict] = []
    for e in snapshot.edges:
        if e.from_id not in node_ids or e.to_id not in node_ids:
            continue
        edges.append({
            "from": e.from_id,
            "to": e.to_id,
            "kind": e.kind,
            "relation_type": e.relation_type,
            "bundle": _bundle_id(domain_of[e.from_id], domain_of[e.to_id]),
        })
    edges.sort(key=lambda e: (e["from"], e["to"], e["kind"]))
    for i, e in enumerate(edges):
        e["id"] = f"e{i}"

    return {"nodes": nodes, "edges": edges}
