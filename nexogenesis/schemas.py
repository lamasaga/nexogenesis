from jsonschema import validate, ValidationError


# 中文命名：汉字 / 字母 / 数字 / 连字符（兼容存量英文 id）
ID_PATTERN = r"^[\u4e00-\u9fffA-Za-z0-9-]+$"

CARD_TYPES = ["domain", "claim", "phenomenon", "model", "method", "entity", "conflict"]

BUFFER_ROLES = [
    "meaning-unit",
    "detail",
    "evidence",
    "artifact-table",
    "artifact-figure",
    "tension",
    "link-hypothesis",
    "profile-seed",
]

CARD_SCHEMA = {
    "type": "object",
    "required": [
        "id", "title", "type", "maturity", "lifecycle",
        "domains", "origin", "sources", "relations", "created", "updated",
    ],
    "properties": {
        "id": {"type": "string", "pattern": ID_PATTERN},
        "title": {"type": "string"},
        "type": {"enum": CARD_TYPES},
        "maturity": {"enum": ["seed", "growing", "mature"]},
        "lifecycle": {"enum": ["active", "superseded", "archived"]},
        "domains": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        "origin": {"enum": ["user", "system", "document", "external"]},
        "sources": {"type": "array", "items": {"type": "string"}},
        "relations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["target", "type"],
                "properties": {
                    "target": {"type": "string"},
                    "type": {
                        "enum": [
                            "extends", "supports", "conflicts-with", "involves",
                            "example-of", "applies-to", "based-on", "influences",
                        ]
                    },
                    "note": {"type": "string"},
                },
            },
        },
        "created": {"type": "string"},
        "updated": {"type": "string"},
        "theory_status": {"enum": ["draft", "active", "dormant"]},
        "superseded_by": {"type": "string"},
    },
}

BUFFER_SCHEMA = {
    "type": "object",
    "required": ["title", "role", "created", "updated", "source", "status"],
    "properties": {
        "title": {"type": "string"},
        "role": {"enum": BUFFER_ROLES},
        "created": {"type": "string"},
        "updated": {"type": "string"},
        "source": {"type": "string"},
        "status": {"enum": ["scratch", "digested", "constructed"]},
        "genre": {"type": "string"},
        "perspective": {"enum": ["self", "external"]},
        "proposed_card_type": {"enum": CARD_TYPES},
        "proposed_domains": {"type": "array", "items": {"type": "string"}},
        "related_within_batch": {
            "type": "array",
            "items": {"type": "string"},
        },
        # 禁止字段不在 properties 中强制；由额外检查拦截
    },
    "additionalProperties": True,
}


def validate_card_schema(data: dict) -> list[str]:
    try:
        validate(instance=data, schema=CARD_SCHEMA)
        return []
    except ValidationError as e:
        return [f"schema error: {e.message} at {list(e.path)}"]


def validate_buffer_schema(data: dict) -> list[str]:
    errors: list[str] = []
    try:
        validate(instance=data, schema=BUFFER_SCHEMA)
    except ValidationError as e:
        errors.append(f"schema error: {e.message} at {list(e.path)}")
    for forbidden in ("id", "relations"):
        if forbidden in data:
            errors.append(f"Buffer 不得包含字段 {forbidden}")
    if "type" in data and data.get("type") in CARD_TYPES:
        errors.append("Buffer 不得使用 Card 的 type 七型；请使用 role")
    return errors
