"""写入后刷新可重建索引（图 + RAG）与陈旧检测。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click


def refresh_derived_indexes(
    root: Path,
    *,
    graph: bool = True,
    rag: bool = True,
    rag_kinds: list[str] | None = None,
    quiet: bool = False,
) -> None:
    root = root.resolve()
    warnings: list[str] = []

    if graph:
        try:
            from nexogenesis.graph.build import rebuild_graph

            snap = rebuild_graph(root)
            if not quiet:
                click.echo(
                    f"Graph rebuilt: nodes={snap.node_count} edges={snap.edge_count}"
                )
        except Exception as exc:
            warnings.append(f"graph rebuild: {exc}")

    if rag:
        try:
            from nexogenesis.rag.index import index_rag

            kinds = rag_kinds or [
                "card_excerpt",
                "buffer",
                "archive",
                "discussion",
                "outbox",
            ]
            stats = index_rag(root, kinds=kinds, full=False, incremental=True)
            if not quiet:
                click.echo(f"RAG indexed: chunks={stats.get('chunk_count', 0)}")
        except Exception as exc:
            warnings.append(f"rag index: {exc}")

    for w in warnings:
        click.echo(f"WARNING: {w}")


def _latest_mtime(paths: list[Path]) -> float:
    latest = 0.0
    for p in paths:
        if p.exists():
            latest = max(latest, p.stat().st_mtime)
    return latest


def _collect_card_files(cards_dir: Path) -> list[Path]:
    if not cards_dir.exists():
        return []
    return [p for p in cards_dir.glob("*.md") if not p.name.startswith("_")]


def _collect_rag_source_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    for rel in (
        "03-Archive",
        "05-Buffer",
        "04-OutBox",
        "04-OutBox/discussions",
        "01-Cards",
    ):
        base = root / rel
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file() and p.suffix.lower() in (".md", ".txt", ".markdown"):
                if p.name.startswith("_"):
                    continue
                paths.append(p)
    return paths


def check_index_staleness(root: Path) -> tuple[list[str], list[str]]:
    """返回 (issues, warnings)。"""
    root = root.resolve()
    issues: list[str] = []
    warnings: list[str] = []

    cards_dir = root / "01-Cards"
    card_files = _collect_card_files(cards_dir)
    card_count = len(card_files)

    graph_stats_path = root / ".nexogenesis" / "graph" / "stats.json"
    if card_count > 0:
        if not graph_stats_path.exists():
            warnings.append("已有卡片但缺少 graph 索引；建议运行 graph rebuild")
        else:
            stats = json.loads(graph_stats_path.read_text(encoding="utf-8"))
            if int(stats.get("node_count", 0)) != card_count:
                warnings.append(
                    f"graph 节点数 ({stats.get('node_count')}) ≠ 卡片数 ({card_count})；"
                    "建议 graph rebuild"
                )
            built = stats.get("built_at", "")
            if card_files and built:
                try:
                    built_dt = datetime.fromisoformat(built.replace("Z", "+00:00"))
                    if _latest_mtime(card_files) > built_dt.timestamp() + 1:
                        warnings.append("卡片晚于 graph 索引；建议 graph rebuild")
                except ValueError:
                    pass

    rag_stats_path = root / ".nexogenesis" / "rag" / "last_build.json"
    rag_sources = _collect_rag_source_files(root)
    if rag_sources and not rag_stats_path.exists():
        warnings.append("存在语料但缺少 RAG 索引；建议 rag index")
    elif rag_stats_path.exists() and rag_sources:
        rag_stats = json.loads(rag_stats_path.read_text(encoding="utf-8"))
        indexed_at = rag_stats.get("indexed_at", "")
        if indexed_at:
            try:
                idx_dt = datetime.fromisoformat(indexed_at.replace("Z", "+00:00"))
                if _latest_mtime(rag_sources) > idx_dt.timestamp() + 1:
                    warnings.append("语料晚于 RAG 索引；建议 rag index")
            except ValueError:
                pass

    return issues, warnings
