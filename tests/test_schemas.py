from nexogenesis.schemas import validate_buffer_schema, validate_card_schema


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


def test_valid_chinese_id():
    data = {
        "id": "语音系统是英语学习的核心",
        "title": "T",
        "type": "claim",
        "maturity": "growing",
        "lifecycle": "active",
        "domains": ["教学"],
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


def test_valid_buffer():
    data = {
        "title": "测试",
        "role": "meaning-unit",
        "created": "2026-07-27",
        "updated": "2026-07-27",
        "source": "s",
        "status": "scratch",
    }
    assert validate_buffer_schema(data) == []


def test_buffer_rejects_card_type_field():
    data = {
        "title": "测试",
        "role": "meaning-unit",
        "type": "claim",
        "created": "2026-07-27",
        "updated": "2026-07-27",
        "source": "s",
        "status": "scratch",
    }
    errors = validate_buffer_schema(data)
    assert any("type" in e for e in errors)
