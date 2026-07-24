from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class BatchOperation:
    operation_id: str
    source: str
    approved_by: str
    writes: list[dict[str, Any]]

    @classmethod
    def from_file(cls, path: Path) -> "BatchOperation":
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        op = data.get("operation", {})
        return cls(
            operation_id=op["id"],
            source=op["source"],
            approved_by=op["approved_by"],
            writes=data.get("writes", []),
        )


def card_meta_from_write(item: dict[str, Any]) -> dict[str, Any]:
    meta = {
        "id": item["id"],
        "title": item["title"],
        "type": item["type"],
        "maturity": item["maturity"],
        "lifecycle": item["lifecycle"],
        "domains": item["domains"],
        "origin": item["origin"],
        "sources": item.get("sources", []),
        "relations": item.get("relations", []),
        "created": item["created"],
        "updated": item["updated"],
    }
    if item.get("theory_status"):
        meta["theory_status"] = item["theory_status"]
    if item.get("superseded_by"):
        meta["superseded_by"] = item["superseded_by"]
    return meta
