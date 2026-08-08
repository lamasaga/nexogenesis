import pytest
from fastapi.testclient import TestClient

from nexogenesis.runtime.api import create_app


@pytest.fixture
def client(kb_root):
    return TestClient(create_app(kb_root))


def test_graph_endpoint(client):
    r = client.get("/api/graph")
    assert r.status_code == 200
    data = r.json()
    assert len(data["nodes"]) == 5
    for n in data["nodes"]:
        assert isinstance(n["x"], float) and isinstance(n["y"], float)
    assert len(data["edges"]) > 0


def test_graph_layout_stable_across_calls(client):
    a = client.get("/api/graph").json()
    b = client.get("/api/graph").json()
    assert a == b


def test_stats_endpoint(client):
    r = client.get("/api/graph/stats")
    assert r.status_code == 200
    stats = r.json()
    assert stats["node_count"] == 5
    assert stats["edge_count"] > 0


def test_card_endpoint(client):
    r = client.get("/api/cards/card-a")
    assert r.status_code == 200
    card = r.json()
    assert card["title"] == "卡片A"
    assert card["type"] == "claim"
    assert "正文" in card["body"]


def test_card_404(client):
    assert client.get("/api/cards/nonexistent").status_code == 404
