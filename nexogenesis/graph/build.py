from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from nexogenesis.graph.model import Edge, GraphSnapshot
from nexogenesis.store import Store, WIKILINK_RE
from nexogenesis.yaml_utils import atomic_write_file


def graph_dir(root: Path) -> Path:
    return root / ".nexogenesis" / "graph"


def build_edges(store: Store) -> list[Edge]:
    edges: list[Edge] = []
    seen: set[tuple[str, str, str, str | None]] = set()

    def add(edge: Edge) -> None:
        key = (edge.from_id, edge.to_id, edge.kind, edge.relation_type)
        if key in seen:
            return
        if edge.from_id == edge.to_id:
            return
        seen.add(key)
        edges.append(edge)

    for cid, card in store.cards.items():
        if card.lifecycle.value == "archived":
            continue
        for rel in card.relations:
            if rel.target not in store.cards:
                continue
            add(Edge(cid, rel.target, "relation", rel.type.value))
        for d in card.domains:
            if d in store.cards:
                add(Edge(cid, d, "domain", None))
        for m in WIKILINK_RE.finditer(card.body or ""):
            target = m.group(1).strip()
            if target and target in store.cards:
                add(Edge(cid, target, "wikilink", None))

    return edges


def build_snapshot(store: Store) -> GraphSnapshot:
    edges = build_edges(store)
    return GraphSnapshot(
        node_count=len(store.cards),
        edge_count=len(edges),
        edges=edges,
        built_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def save_snapshot(root: Path, snapshot: GraphSnapshot) -> None:
    gdir = graph_dir(root)
    gdir.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(e.to_dict(), ensure_ascii=False) for e in snapshot.edges]
    atomic_write_file(gdir / "edges.jsonl", "\n".join(lines) + ("\n" if lines else ""))
    atomic_write_file(
        gdir / "stats.json",
        json.dumps(snapshot.to_stats_dict(), ensure_ascii=False, indent=2) + "\n",
    )


def load_snapshot(root: Path) -> GraphSnapshot | None:
    stats_path = graph_dir(root) / "stats.json"
    edges_path = graph_dir(root) / "edges.jsonl"
    if not stats_path.exists() or not edges_path.exists():
        return None
    stats = json.loads(stats_path.read_text(encoding="utf-8"))
    edges: list[Edge] = []
    for line in edges_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            edges.append(Edge.from_dict(json.loads(line)))
    return GraphSnapshot(
        node_count=int(stats.get("node_count", 0)),
        edge_count=len(edges),
        edges=edges,
        built_at=str(stats.get("built_at", "")),
    )


def rebuild_graph(root: Path) -> GraphSnapshot:
    store = Store(root / "01-Cards").load()
    snapshot = build_snapshot(store)
    save_snapshot(root, snapshot)
    return snapshot
