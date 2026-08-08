from nexogenesis.runtime.graph_data import build_graph_payload


def test_payload_nodes_and_edges(kb_root):
    payload = build_graph_payload(kb_root)
    node_ids = {n["id"] for n in payload["nodes"]}
    assert node_ids == {"domain-alpha", "domain-beta", "card-a", "card-b", "card-c"}
    assert len(payload["edges"]) > 0
    for e in payload["edges"]:
        assert e["id"]
        assert e["from"] in node_ids and e["to"] in node_ids
        assert e["bundle"]


def test_bundle_grouping(kb_root):
    payload = build_graph_payload(kb_root)
    # card-a → card-b 是跨域关系边，束 id 为排序后的 domain 对
    rel = [e for e in payload["edges"]
           if e["from"] == "card-a" and e["to"] == "card-b"
           and e["kind"] == "relation"][0]
    assert rel["bundle"] == "domain-alpha::domain-beta"
    # card-a → domain-alpha 是域内边，束 id 即 domain 自身
    dom = [e for e in payload["edges"]
           if e["from"] == "card-a" and e["to"] == "domain-alpha"][0]
    assert dom["bundle"] == "domain-alpha"


def test_relation_type_preserved(kb_root):
    payload = build_graph_payload(kb_root)
    cw = [e for e in payload["edges"] if e.get("relation_type") == "conflicts-with"]
    assert len(cw) == 1
