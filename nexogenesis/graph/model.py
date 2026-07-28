from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Edge:
    from_id: str
    to_id: str
    kind: str  # relation | wikilink | domain
    relation_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "from": self.from_id,
            "to": self.to_id,
            "kind": self.kind,
        }
        if self.relation_type:
            d["relation_type"] = self.relation_type
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Edge":
        return cls(
            from_id=data["from"],
            to_id=data["to"],
            kind=data["kind"],
            relation_type=data.get("relation_type"),
        )


@dataclass
class GraphSnapshot:
    node_count: int
    edge_count: int
    edges: list[Edge] = field(default_factory=list)
    built_at: str = ""

    def adjacency(self) -> dict[str, list[Edge]]:
        adj: dict[str, list[Edge]] = {}
        for e in self.edges:
            adj.setdefault(e.from_id, []).append(e)
        return adj

    def to_stats_dict(self) -> dict[str, Any]:
        by_kind: dict[str, int] = {}
        for e in self.edges:
            by_kind[e.kind] = by_kind.get(e.kind, 0) + 1
        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "edges_by_kind": by_kind,
            "built_at": self.built_at,
        }
