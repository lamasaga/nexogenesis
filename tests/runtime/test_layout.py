import json
import math

from nexogenesis.runtime.graph_data import build_graph_payload
from nexogenesis.runtime.layout import compute_layout, ensure_layout, LAYOUT_REL


def _dist(a, b):
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


def test_compute_layout_deterministic(kb_root):
    payload = build_graph_payload(kb_root)
    p1 = compute_layout(payload["nodes"], payload["edges"])
    p2 = compute_layout(payload["nodes"], payload["edges"])
    assert p1 == p2
    assert set(p1) == {n["id"] for n in payload["nodes"]}
    for pos in p1.values():
        assert isinstance(pos["x"], float) and isinstance(pos["y"], float)


def test_connected_nodes_closer_than_average(kb_root):
    """力导向的核心性质：有边节点对的平均距离显著小于任意节点对。

    5 卡小图两点内全连通，对比弱；用 4 域 × 12 卡合成图验证结构涌现。
    """
    nodes, edges = [], []
    for d in range(4):
        dom = f"d{d}"
        nodes.append({"id": dom, "title": dom, "type": "domain",
                      "domains": [dom], "x": 0, "y": 0})
        for i in range(12):
            cid = f"{dom}-c{i}"
            nodes.append({"id": cid, "title": cid, "type": "claim",
                          "domains": [dom], "x": 0, "y": 0})
            edges.append({"id": f"e-{cid}", "from": cid, "to": dom,
                          "kind": "domain", "relation_type": None,
                          "bundle": dom})
            if i > 0:
                edges.append({"id": f"e-{cid}-p", "from": cid,
                              "to": f"{dom}-c{i-1}", "kind": "relation",
                              "relation_type": "supports", "bundle": dom})
    for d in range(4):  # 稀疏跨域链
        edges.append({"id": f"ex-{d}", "from": f"d{d}-c0",
                      "to": f"d{(d+1)%4}-c0", "kind": "relation",
                      "relation_type": "supports",
                      "bundle": "::".join(sorted([f"d{d}", f"d{(d+1)%4}"]))})
    pos = compute_layout(nodes, edges)
    edge_dists = [_dist(pos[e["from"]], pos[e["to"]]) for e in edges]
    ids = [n["id"] for n in nodes]
    all_dists = [_dist(pos[a], pos[b])
                 for i, a in enumerate(ids) for b in ids[i + 1:]]
    assert sum(edge_dists) / len(edge_dists) < 0.6 * (sum(all_dists) / len(all_dists))


def test_same_domain_clusters_together(kb_root):
    payload = build_graph_payload(kb_root)
    pos = compute_layout(payload["nodes"], payload["edges"])
    # 同域且有边相连的卡应靠近其 domain 卡
    assert _dist(pos["card-a"], pos["domain-alpha"]) < 150
    assert _dist(pos["card-c"], pos["domain-alpha"]) < 150


def test_ensure_layout_persists_and_fills(kb_root):
    payload = build_graph_payload(kb_root)
    nodes, edges = payload["nodes"], payload["edges"]
    pos1 = ensure_layout(kb_root, nodes, edges)
    layout_file = kb_root / LAYOUT_REL
    assert layout_file.exists()
    saved = json.loads(layout_file.read_text(encoding="utf-8"))
    assert saved == pos1
    # 新增节点：补算成功；已有节点仅小幅漂移（软钉）
    nodes2 = nodes + [{"id": "card-new", "title": "新卡", "type": "claim",
                       "domains": ["domain-beta"]}]
    edges2 = edges + [{"id": "eX", "from": "card-new", "to": "card-b",
                       "kind": "relation", "relation_type": "supports",
                       "bundle": "domain-beta"}]
    pos2 = ensure_layout(kb_root, nodes2, edges2)
    assert "card-new" in pos2
    for cid in pos1:
        assert _dist(pos1[cid], pos2[cid]) < 60
    # 新卡应落在其邻接卡附近（吸引力生效）
    assert _dist(pos2["card-new"], pos2["card-b"]) < 200
