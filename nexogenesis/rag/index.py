from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nexogenesis.rag.corpus import CORPUS_KINDS, Chunk, collect_chunks
from nexogenesis.yaml_utils import atomic_write_file


def rag_dir(root: Path) -> Path:
    return root / ".nexogenesis" / "rag"


def _db_path(root: Path) -> Path:
    return rag_dir(root) / "chunks.db"


def _connect(root: Path) -> sqlite3.Connection:
    rag_dir(root).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_db_path(root))
    conn.row_factory = sqlite3.Row
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks_meta (
            chunk_id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            path TEXT NOT NULL,
            anchor TEXT NOT NULL,
            attribution TEXT NOT NULL,
            linked_cards TEXT NOT NULL,
            body TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            chunk_id UNINDEXED,
            kind UNINDEXED,
            path UNINDEXED,
            anchor UNINDEXED,
            attribution UNINDEXED,
            linked_cards UNINDEXED,
            body,
            tokenize='unicode61'
        )
        """
    )


def _fingerprint_path(root: Path, rel_path: str) -> dict[str, float | int] | None:
    p = root / Path(rel_path.replace("/", "\\")) if "\\" not in rel_path else root / rel_path
    try:
        st = p.stat()
        return {"mtime": st.st_mtime, "size": st.st_size}
    except OSError:
        return None


def _delete_path_chunks(conn: sqlite3.Connection, path: str) -> None:
    rows = conn.execute(
        "SELECT chunk_id FROM chunks_meta WHERE path = ?", (path,)
    ).fetchall()
    for row in rows:
        conn.execute("DELETE FROM chunks_fts WHERE chunk_id = ?", (row["chunk_id"],))
    conn.execute("DELETE FROM chunks_meta WHERE path = ?", (path,))


def _insert_chunk(conn: sqlite3.Connection, ch: Chunk) -> None:
    row = ch.to_row()
    conn.execute(
        """
        INSERT OR REPLACE INTO chunks_meta
        (chunk_id, kind, path, anchor, attribution, linked_cards, body)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row["chunk_id"],
            row["kind"],
            row["path"],
            row["anchor"],
            row["attribution"],
            row["linked_cards"],
            row["body"],
        ),
    )
    conn.execute("DELETE FROM chunks_fts WHERE chunk_id = ?", (row["chunk_id"],))
    conn.execute(
        """
        INSERT INTO chunks_fts
        (chunk_id, kind, path, anchor, attribution, linked_cards, body)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row["chunk_id"],
            row["kind"],
            row["path"],
            row["anchor"],
            row["attribution"],
            row["linked_cards"],
            row["body"],
        ),
    )


def _load_old_sources(root: Path) -> dict[str, Any]:
    path = rag_dir(root) / "last_build.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return dict(data.get("sources") or {})


def index_rag(
    root: Path,
    *,
    kinds: list[str] | None = None,
    full: bool = False,
    incremental: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    allowed = set(kinds) if kinds else set(CORPUS_KINDS)
    chunks = collect_chunks(root, kinds=allowed)

    by_path: dict[str, list[Chunk]] = {}
    for ch in chunks:
        by_path.setdefault(ch.path, []).append(ch)

    new_sources: dict[str, Any] = {}
    for path in by_path:
        fp = _fingerprint_path(root, path)
        if fp:
            new_sources[path] = fp

    old_sources = _load_old_sources(root)
    do_full = full or not incremental or not _db_path(root).exists()

    conn = _connect(root)
    try:
        _init_schema(conn)
        if do_full:
            conn.execute("DELETE FROM chunks_meta")
            conn.execute("DELETE FROM chunks_fts")
            paths_to_write = set(by_path.keys())
        else:
            paths_to_write = set()
            for path in by_path:
                if path not in old_sources or old_sources.get(path) != new_sources.get(path):
                    paths_to_write.add(path)
            removed = set(old_sources.keys()) - set(by_path.keys())
            for path in removed:
                _delete_path_chunks(conn, path)
            for path in paths_to_write:
                _delete_path_chunks(conn, path)

        for path in paths_to_write:
            for ch in by_path.get(path, []):
                _insert_chunk(conn, ch)
        conn.commit()
    finally:
        conn.close()

    by_kind: dict[str, int] = {}
    for ch in chunks:
        by_kind[ch.kind] = by_kind.get(ch.kind, 0) + 1

    stats = {
        "chunk_count": len(chunks),
        "by_kind": by_kind,
        "indexed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kinds": sorted(allowed),
        "sources": new_sources,
        "incremental": not do_full,
        "updated_paths": len(paths_to_write) if not do_full else len(by_path),
    }
    atomic_write_file(
        rag_dir(root) / "last_build.json",
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n",
    )
    manifest = rag_dir(root) / "manifest.jsonl"
    lines = [json.dumps(ch.to_row(), ensure_ascii=False) for ch in chunks]
    atomic_write_file(manifest, "\n".join(lines) + ("\n" if lines else ""))

    return stats


def rag_stats(root: Path) -> dict[str, Any]:
    root = root.resolve()
    path = rag_dir(root) / "last_build.json"
    if not path.exists():
        return {"chunk_count": 0, "indexed_at": None}
    return json.loads(path.read_text(encoding="utf-8"))
