from nexogenesis.schemas import validate_card_schema


def test_valid_card():
    data = {
        "id": "test",
        "title": "T",
        "type": "claim",
        "maturity": "growing",
        "lifecycle": "active",
        "domains": ["teaching"],
        "origin": "user",
        "sources": ["s"],
        "relations": [],
        "created": "2026-07-24",
        "updated": "2026-07-24",
    }
    assert validate_card_schema(data) == []


def test_invalid_type():
    data = {
        "id": "test",
        "title": "T",
        "type": "note",
        "maturity": "growing",
        "lifecycle": "active",
        "domains": ["teaching"],
        "origin": "user",
        "sources": ["s"],
        "relations": [],
        "created": "2026-07-24",
        "updated": "2026-07-24",
    }
    errors = validate_card_schema(data)
    assert any("note" in e for e in errors)
