import json

from nexogenesis.runtime.graph_data import build_graph_payload
from nexogenesis.runtime.layout import compute_layout, ensure_layout, LAYOUT_REL


def test_compute_layout_deterministic(kb_root):
    nodes = build_graph_payload(kb_root)["nodes"]
    p1 = compute_layout(nodes)
    p2 = compute_layout(nodes)
    assert p1 == p2
    assert set(p1) == {n["id"] for n in nodes}
    for pos in p1.values():
        assert isinstance(pos["x"], float) and isinstance(pos["y"], float)


def test_same_domain_clusters_together(kb_root):
    nodes = build_graph_payload(kb_root)["nodes"]
    pos = compute_layout(nodes)
    # 同域节点的质心应靠近其 domain 卡坐标
    cx = (pos["card-a"]["x"] + pos["card-c"]["x"]) / 2
    cy = (pos["card-a"]["y"] + pos["card-c"]["y"]) / 2
    dx = cx - pos["domain-alpha"]["x"]
    dy = cy - pos["domain-alpha"]["y"]
    assert (dx * dx + dy * dy) ** 0.5 < 120


def test_ensure_layout_persists_and_fills(kb_root):
    nodes = build_graph_payload(kb_root)["nodes"]
    pos1 = ensure_layout(kb_root, nodes)
    layout_file = kb_root / LAYOUT_REL
    assert layout_file.exists()
    saved = json.loads(layout_file.read_text(encoding="utf-8"))
    assert saved == pos1
    # 再来一个未知节点：只补算它，已有坐标不变
    nodes2 = nodes + [{"id": "card-new", "title": "新卡", "type": "claim",
                       "domains": ["domain-beta"]}]
    pos2 = ensure_layout(kb_root, nodes2)
    assert "card-new" in pos2
    for cid in pos1:
        assert pos2[cid] == pos1[cid]
