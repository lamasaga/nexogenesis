from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from nexogenesis.graph.retrieve import graph_retrieve, tokenize
from nexogenesis.rag.search import rag_search, rag_search_for_cards
from nexogenesis.yaml_utils import atomic_write_file

MODES = ("talk", "answer", "digest", "construct", "judge")

MODE_RAG_KINDS: dict[str, list[str]] = {
    "talk": ["discussion", "archive", "outbox", "card_excerpt"],
    "answer": ["discussion", "archive", "outbox", "card_excerpt"],
    "digest": ["buffer", "archive", "discussion"],
    "construct": ["card_excerpt", "discussion"],
    "judge": ["discussion", "archive", "card_excerpt"],
}

MODE_RAG_TOP: dict[str, int] = {
    "talk": 8,
    "answer": 8,
    "digest": 10,
    "construct": 4,
    "judge": 6,
}


def build_context_package(
    root: Path,
    *,
    query: str = "",
    mode: str = "talk",
    seeds: list[str] | None = None,
    buffer_tokens: set[str] | None = None,
    budget_chars: int = 16000,
    graph_hops: int = 2,
    graph_nodes: int = 24,
    rag_top: int | None = None,
    use_graph: bool = True,
    use_rag: bool = True,
    use_attention: bool = True,
    use_stm: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    mode = mode if mode in MODES else "talk"

    # talk/answer/judge/digest：默认走注意力双账户组装
    if use_attention and mode in ("talk", "answer", "judge", "digest"):
        from nexogenesis.thinking.assemble import assemble_working_set

        pkg = assemble_working_set(
            root,
            query=query,
            mode=mode,
            seeds=seeds,
            buffer_tokens=buffer_tokens,
            use_stm=use_stm,
            use_graph=use_graph,
            use_rag=use_rag,
        )
        # CLI 显式预算可收紧 rag_top / chars（不破坏双账户）
        if rag_top is not None and pkg.get("material"):
            pkg["material"] = pkg["material"][:rag_top]
            pkg["budget"]["rag_chunks"] = len(pkg["material"])
        return pkg

    structure: dict[str, Any] = {
        "seeds": [],
        "nodes": [],
        "edges": [],
    }
    status = "ok"
    blind_spots: list[str] = []

    if use_graph:
        structure = graph_retrieve(
            root,
            query=query,
            seeds=seeds,
            buffer_tokens=buffer_tokens,
            max_hops=graph_hops,
            max_nodes=graph_nodes,
            max_chars=budget_chars // 2,
            rebuild=False,
        )
        status = structure.get("status", "ok")
        if status == "empty-graph":
            blind_spots.extend(structure.get("blind_spots") or [])
    else:
        structure = {"status": "skipped", "nodes": [], "edges": [], "seeds": []}

    material: list[dict[str, Any]] = []
    rag_budget = budget_chars // 2

    if use_rag:
        kinds = MODE_RAG_KINDS.get(mode, MODE_RAG_KINDS["talk"])
        top_n = rag_top if rag_top is not None else MODE_RAG_TOP.get(mode, 8)
        hits = rag_search(root, query, kinds=kinds, top=top_n)

        card_ids = [n["id"] for n in structure.get("nodes") or []]
        if card_ids:
            linked_hits = rag_search_for_cards(root, card_ids[:6], top_per_card=2)
            seen = {h["chunk_id"] for h in hits}
            for h in linked_hits:
                if h["chunk_id"] not in seen:
                    hits.append(h)
                    seen.add(h["chunk_id"])

        used = 0
        for h in hits:
            cost = len(h.get("excerpt") or "")
            if used + cost > rag_budget and material:
                break
            used += cost
            material.append({
                "chunk_id": h["chunk_id"],
                "kind": h["kind"],
                "attribution": h["attribution"],
                "anchor": h["anchor"],
                "excerpt": h["excerpt"],
                "linked_cards": h.get("linked_cards") or [],
            })

        if not hits and query.strip():
            blind_spots.append("RAG 无命中；可运行 rag index 或扩充语料。")
    else:
        blind_spots.append("RAG 已禁用（--no-rag）。")

    if not use_graph:
        blind_spots.append("图检索已禁用（--no-graph）。")

    pkg = {
        "query": query,
        "mode": mode,
        "status": status if structure.get("nodes") or material else "empty",
        "structure": {
            "seeds": structure.get("seeds") or [],
            "nodes": structure.get("nodes") or [],
            "edges": structure.get("edges") or [],
        },
        "material": material,
        "blind_spots": blind_spots,
        "budget": {
            "chars": sum(len(n.get("excerpt") or "") for n in structure.get("nodes") or [])
            + sum(len(m.get("excerpt") or "") for m in material),
            "structure_nodes": len(structure.get("nodes") or []),
            "rag_chunks": len(material),
        },
    }
    return pkg


def save_context_package(root: Path, pkg: dict[str, Any], *, name: str = "context") -> Path:
    out_dir = root / ".nexogenesis" / "tmp" / "retrieve"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.yaml"
    atomic_write_file(path, yaml.safe_dump(pkg, allow_unicode=True, sort_keys=False))
    return path


def seeds_from_buffers(buffers: list[dict]) -> set[str]:
    from nexogenesis.ingest.context_pack import _tokens_from_buffers

    return _tokens_from_buffers(buffers)


def format_material_excerpt(material: list[dict], *, max_items: int = 6) -> str:
    lines = []
    for m in material[:max_items]:
        lines.append(
            f"- [{m.get('kind')}|{m.get('attribution')}] {m.get('anchor')}\n"
            f"  { (m.get('excerpt') or '')[:400] }"
        )
    return "\n".join(lines)


def deep_cards_from_graph(
    root: Path,
    buffers: list[dict],
    *,
    max_deep: int = 6,
) -> list[dict] | None:
    """digest 用：图检索深读卡；失败返回 None 以回退启发式。"""
    from nexogenesis.store import Store

    store = Store(root / "01-Cards").load()
    if not store.cards:
        return None

    btokens = seeds_from_buffers(buffers)
    pkg = build_context_package(
        root,
        query=" ".join(sorted(btokens)[:20]),
        mode="digest",
        buffer_tokens=btokens,
        graph_nodes=max_deep,
        rag_top=0,
        use_rag=False,
    )
    nodes = pkg.get("structure", {}).get("nodes") or []
    if not nodes:
        return None

    out = []
    for n in nodes[:max_deep]:
        c = store.cards.get(n["id"])
        if not c:
            continue
        out.append({
            "id": c.id,
            "title": c.title,
            "type": c.type.value,
            "domains": list(c.domains),
            "relations": [
                {"target": r.target, "type": r.type.value, "note": r.note}
                for r in c.relations
            ],
            "body": c.body or "",
        })
    return out if out else None
