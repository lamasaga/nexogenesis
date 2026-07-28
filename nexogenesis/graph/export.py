from __future__ import annotations

import html
import json
from pathlib import Path

from nexogenesis.graph.build import load_snapshot, rebuild_graph
from nexogenesis.models import CardType
from nexogenesis.store import Store
from nexogenesis.yaml_utils import atomic_write_file


def export_graphml(
    root: Path,
    *,
    center: str | None = None,
    hops: int = 2,
    rebuild: bool = False,
) -> str:
    root = root.resolve()
    store = Store(root / "01-Cards").load()
    snapshot = load_snapshot(root)
    if snapshot is None or rebuild:
        snapshot = rebuild_graph(root)

    node_ids = set(store.cards.keys())
    if center and center in store.cards:
        from nexogenesis.graph.traverse import expand_subgraph

        visited = expand_subgraph(
            store, snapshot, [center], max_hops=hops, max_nodes=80
        )
        node_ids = set(visited.keys())

    id_map = {cid: f"n{i}" for i, cid in enumerate(sorted(node_ids))}

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
        '  <key id="label" for="node" attr.name="label" attr.type="string"/>',
        '  <key id="type" for="node" attr.name="type" attr.type="string"/>',
        '  <key id="kind" for="edge" attr.name="kind" attr.type="string"/>',
        '  <key id="relation_type" for="edge" attr.name="relation_type" attr.type="string"/>',
        '  <graph id="G" edgedefault="directed">',
    ]

    for cid in sorted(node_ids):
        c = store.cards[cid]
        nid = id_map[cid]
        label = html.escape(f"{c.title} ({c.type.value})")
        lines.append(
            f'    <node id="{nid}"><data key="label">{label}</data>'
            f'<data key="type">{c.type.value}</data></node>'
        )

    eidx = 0
    for e in snapshot.edges:
        if e.from_id not in node_ids or e.to_id not in node_ids:
            continue
        src = id_map[e.from_id]
        tgt = id_map[e.to_id]
        rt = html.escape(e.relation_type or "")
        kind = html.escape(e.kind)
        lines.append(
            f'    <edge id="e{eidx}" source="{src}" target="{tgt}">'
            f'<data key="kind">{kind}</data>'
            f'<data key="relation_type">{rt}</data></edge>'
        )
        eidx += 1

    lines.append("  </graph>")
    lines.append("</graphml>")
    return "\n".join(lines) + "\n"


def write_graphml(
    root: Path,
    out_path: Path,
    *,
    center: str | None = None,
    hops: int = 2,
    rebuild: bool = False,
) -> Path:
    text = export_graphml(root, center=center, hops=hops, rebuild=rebuild)
    atomic_write_file(out_path, text)
    return out_path
