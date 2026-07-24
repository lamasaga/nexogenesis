from nexogenesis.models import Card, CardType, Maturity, Lifecycle, Origin, RelationType


def test_card_from_dict():
    data = {
        "title": "测试主张",
        "type": "claim",
        "maturity": "growing",
        "lifecycle": "active",
        "domains": ["teaching"],
        "origin": "user",
        "sources": ["2026-07-24 对话"],
        "relations": [{"target": "other", "type": "supports"}],
        "created": "2026-07-24",
        "updated": "2026-07-24",
    }
    card = Card.from_dict("test-claim", data, "正文")
    assert card.type == CardType.CLAIM
    assert card.maturity == Maturity.GROWING
    assert card.relations[0].type == RelationType.SUPPORTS
