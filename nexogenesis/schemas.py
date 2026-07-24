from jsonschema import validate, ValidationError


CARD_SCHEMA = {
    "type": "object",
    "required": [
        "id", "title", "type", "maturity", "lifecycle",
        "domains", "origin", "sources", "relations", "created", "updated",
    ],
    "properties": {
        "id": {"type": "string", "pattern": "^[a-z0-9-]+$"},
        "title": {"type": "string"},
        "type": {"enum": ["domain", "claim", "phenomenon", "model", "method", "entity", "conflict"]},
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
                    "type": {"enum": ["extends", "supports", "conflicts-with", "involves", "example-of", "applies-to", "based-on", "influences"]},
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


def validate_card_schema(data: dict) -> list[str]:
    try:
        validate(instance=data, schema=CARD_SCHEMA)
        return []
    except ValidationError as e:
        return [f"schema error: {e.message} at {list(e.path)}"]
