"""深读工作集应优先 pin 领域骨架（v3.1 滋养式）。"""

from pathlib import Path

from nexogenesis.ingest.context_pack import pin_domain_skeleton, select_deep_cards
from nexogenesis.models import Card, CardType, Maturity, Lifecycle, Origin
from nexogenesis.store import Store


def _card(cid: str, ctype: CardType, domains: list[str], title: str = "") -> Card:
    return Card(
        id=cid,
        title=title or cid,
        type=ctype,
        maturity=Maturity.GROWING,
        lifecycle=Lifecycle.ACTIVE,
        domains=domains,
        origin=Origin.DOCUMENT,
        sources=["t"],
        relations=[],
        created="2026-07-01",
        updated="2026-07-01",
        body=f"正文 {cid}",
        path=Path(f"{cid}.md"),
    )


def test_pin_domain_skeleton_puts_domains_first(tmp_path: Path):
    store = Store(tmp_path)
    store.cards = {
        "教学": _card("教学", CardType.DOMAIN, []),
        "反馈": _card("反馈", CardType.CLAIM, ["教学"]),
        "脚手架": _card("脚手架", CardType.MODEL, ["教学"]),
    }
    raw = [
        {
            "id": "反馈",
            "type": "claim",
            "title": "反馈",
            "domains": ["教学"],
            "body": "x",
        },
        {
            "id": "脚手架",
            "type": "model",
            "title": "脚手架",
            "domains": ["教学"],
            "body": "y",
        },
    ]
    pinned = pin_domain_skeleton(store, raw, max_deep=3)
    assert pinned[0]["id"] == "教学"
    assert pinned[0]["type"] == "domain"
    assert {c["id"] for c in pinned} >= {"教学", "反馈"}


def test_select_deep_cards_pins_domain_without_graph(tmp_path: Path):
    store = Store(tmp_path)
    store.cards = {
        "教学": _card("教学", CardType.DOMAIN, []),
        "反馈差距": _card("反馈差距", CardType.CLAIM, ["教学"], title="反馈应指出差距"),
    }
    buffers = [{"title": "反馈应指出差距", "text": "关于**反馈差距**的材料", "proposed_domains": ["教学"]}]
    deep = select_deep_cards(store, buffers, max_deep=4, use_graph=False)
    types = [c["type"] for c in deep]
    assert "domain" in types
    assert deep[0]["type"] == "domain" or any(c["id"] == "教学" for c in deep)
