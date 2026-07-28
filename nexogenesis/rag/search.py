from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from nexogenesis.rag.index import _connect, _db_path, rag_stats

_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


def _fts_query(text: str) -> str:
    tokens = [t for t in _TOKEN_RE.findall(text) if len(t) >= 2]
    if not tokens:
        return ""
    return " OR ".join(f'"{t}"' for t in tokens[:12])


def rag_search(
    root: Path,
    query: str,
    *,
    kinds: list[str] | None = None,
    top: int = 12,
    linked_card: str | None = None,
) -> list[dict[str, Any]]:
    root = root.resolve()
    if not _db_path(root).exists():
        return []

    fq = _fts_query(query)
    conn = _connect(root)
    rows: list[sqlite3.Row] = []
    try:
        if linked_card and not fq:
            cur = conn.execute(
                """
                SELECT chunk_id, kind, path, anchor, attribution, linked_cards, body
                FROM chunks_meta
                WHERE linked_cards LIKE ?
                LIMIT ?
                """,
                (f'%"{linked_card}"%', top),
            )
            rows = cur.fetchall()
        elif fq:
            kind_filter = ""
            params: list[Any] = [fq]
            if kinds:
                placeholders = ",".join("?" for _ in kinds)
                kind_filter = f" AND kind IN ({placeholders})"
                params.extend(kinds)
            params.append(top)
            cur = conn.execute(
                f"""
                SELECT chunk_id, kind, path, anchor, attribution, linked_cards, body
                FROM chunks_fts
                WHERE chunks_fts MATCH ?
                {kind_filter}
                LIMIT ?
                """,
                params,
            )
            rows = cur.fetchall()
            if not rows:
                rows = _like_fallback(conn, query, kinds=kinds, top=top)
        elif query.strip():
            rows = _like_fallback(conn, query, kinds=kinds, top=top)
    finally:
        conn.close()

    return _rows_to_hits(rows)


def _like_fallback(
    conn: sqlite3.Connection,
    query: str,
    *,
    kinds: list[str] | None,
    top: int,
) -> list[sqlite3.Row]:
    tokens = [t for t in _TOKEN_RE.findall(query) if len(t) >= 2]
    if not tokens:
        return []
    sql = """
        SELECT chunk_id, kind, path, anchor, attribution, linked_cards, body
        FROM chunks_meta
        WHERE body LIKE ?
    """
    params: list[Any] = [f"%{tokens[0]}%"]
    if kinds:
        sql += f" AND kind IN ({','.join('?' for _ in kinds)})"
        params.extend(kinds)
    sql += " LIMIT ?"
    params.append(top)
    return conn.execute(sql, params).fetchall()


def _rows_to_hits(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for row in rows:
        linked = []
        try:
            linked = json.loads(row["linked_cards"])
        except json.JSONDecodeError:
            pass
        body = row["body"] or ""
        excerpt = body if len(body) <= 600 else body[:580].rstrip() + "…"
        results.append({
            "chunk_id": row["chunk_id"],
            "kind": row["kind"],
            "path": row["path"],
            "anchor": row["anchor"],
            "attribution": row["attribution"],
            "linked_cards": linked,
            "excerpt": excerpt,
        })
    return results


def rag_search_for_cards(
    root: Path,
    card_ids: list[str],
    *,
    top_per_card: int = 3,
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for cid in card_ids:
        hits = rag_search(root, "", linked_card=cid, top=top_per_card)
        for h in hits:
            if h["chunk_id"] not in seen:
                seen.add(h["chunk_id"])
                out.append(h)
    return out
