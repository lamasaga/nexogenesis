from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CardType(str, Enum):
    DOMAIN = "domain"
    CLAIM = "claim"
    PHENOMENON = "phenomenon"
    MODEL = "model"
    METHOD = "method"
    ENTITY = "entity"
    CONFLICT = "conflict"


class RelationType(str, Enum):
    EXTENDS = "extends"
    SUPPORTS = "supports"
    CONFLICTS_WITH = "conflicts-with"
    INVOLVES = "involves"
    EXAMPLE_OF = "example-of"
    APPLIES_TO = "applies-to"
    BASED_ON = "based-on"
    INFLUENCES = "influences"


class Origin(str, Enum):
    USER = "user"
    SYSTEM = "system"
    DOCUMENT = "document"
    EXTERNAL = "external"


class Maturity(str, Enum):
    SEED = "seed"
    GROWING = "growing"
    MATURE = "mature"


class Lifecycle(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class TheoryStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DORMANT = "dormant"


@dataclass
class Relation:
    target: str
    type: RelationType
    note: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Relation":
        return cls(
            target=data["target"],
            type=RelationType(data["type"]),
            note=data.get("note", ""),
        )


@dataclass
class Card:
    id: str
    title: str
    type: CardType
    maturity: Maturity
    lifecycle: Lifecycle
    domains: list[str]
    origin: Origin
    sources: list[str]
    relations: list[Relation]
    created: str
    updated: str
    body: str
    theory_status: TheoryStatus | None = None
    superseded_by: str | None = None
    path: str | None = None

    @classmethod
    def from_dict(cls, id: str, data: dict[str, Any], body: str, path: str | None = None) -> "Card":
        return cls(
            id=id,
            title=data["title"],
            type=CardType(data["type"]),
            maturity=Maturity(data["maturity"]),
            lifecycle=Lifecycle(data["lifecycle"]),
            domains=list(data.get("domains", [])),
            origin=Origin(data["origin"]),
            sources=list(data.get("sources", [])),
            relations=[Relation.from_dict(r) for r in data.get("relations", [])],
            created=data["created"],
            updated=data["updated"],
            body=body,
            theory_status=TheoryStatus(data["theory_status"]) if data.get("theory_status") else None,
            superseded_by=data.get("superseded_by"),
            path=path,
        )


@dataclass
class ProfileQuestion:
    question: str
    added_at: str
    status: str = "active"


@dataclass
class JournalEntry:
    operation_id: str
    timestamp: str
    action: str
    targets: list[str]
    source: str
    approved_by: str
