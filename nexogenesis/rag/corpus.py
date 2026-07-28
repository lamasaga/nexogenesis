from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from nexogenesis.yaml_utils import split_frontmatter

CORPUS_KINDS = ("archive", "buffer", "discussion", "outbox", "card_excerpt")

DISCUSSION_ATTRIBUTION = "nascent"


@dataclass
class Chunk:
    chunk_id: str
    kind: str
    path: str
    anchor: str
    attribution: str
    body: str
    linked_cards: list[str]

    def to_row(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "kind": self.kind,
            "path": self.path,
            "anchor": self.anchor,
            "attribution": self.attribution,
            "linked_cards": json.dumps(self.linked_cards, ensure_ascii=False),
            "body": self.body,
        }


def _chunk_id(path: str, anchor: str, body: str) -> str:
    h = hashlib.sha256(f"{path}|{anchor}|{body[:200]}".encode("utf-8")).hexdigest()[:16]
    return f"chk-{h}"


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _chunks_from_markdown(
    path: Path,
    root: Path,
    *,
    kind: str,
    attribution: str,
    default_linked: list[str] | None = None,
) -> Iterator[Chunk]:
    text = path.read_text(encoding="utf-8", errors="replace")
    meta, body = split_frontmatter(text)
    meta = meta or {}
    rel = _rel(root, path)
    linked = list(default_linked or [])
    if isinstance(meta.get("linked_cards"), list):
        linked = list(meta["linked_cards"])
    title = str(meta.get("title") or path.stem)
    anchor = f"{rel}#{title}"

    if kind == "buffer":
        yield Chunk(
            chunk_id=_chunk_id(rel, anchor, body),
            kind=kind,
            path=rel,
            anchor=anchor,
            attribution=attribution,
            body=body.strip() or text,
            linked_cards=linked,
        )
        return

    if kind == "discussion":
        yield Chunk(
            chunk_id=_chunk_id(rel, anchor, body),
            kind=kind,
            path=rel,
            anchor=anchor,
            attribution=DISCUSSION_ATTRIBUTION,
            body=body.strip() or text,
            linked_cards=linked,
        )
        return

    # archive / outbox / default: split by ## sections
    sections = _split_sections(body)
    if not sections:
        yield Chunk(
            chunk_id=_chunk_id(rel, rel, text),
            kind=kind,
            path=rel,
            anchor=rel,
            attribution=attribution,
            body=text[:12000],
            linked_cards=linked,
        )
        return

    for heading, sec_body in sections:
        sec_anchor = f"{rel}#{heading}" if heading else rel
        content = f"## {heading}\n\n{sec_body}".strip() if heading else sec_body
        yield Chunk(
            chunk_id=_chunk_id(rel, sec_anchor, content),
            kind=kind,
            path=rel,
            anchor=sec_anchor,
            attribution=attribution,
            body=content[:8000],
            linked_cards=linked,
        )


def _split_sections(body: str) -> list[tuple[str, str]]:
    parts: list[tuple[str, str]] = []
    current_heading = ""
    current_lines: list[str] = []
    for line in (body or "").splitlines():
        if line.startswith("## "):
            if current_lines or current_heading:
                parts.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines or current_heading:
        parts.append((current_heading, "\n".join(current_lines).strip()))
    return parts


def collect_chunks(
    root: Path,
    kinds: set[str] | None = None,
) -> list[Chunk]:
    root = root.resolve()
    allowed = kinds or set(CORPUS_KINDS)
    chunks: list[Chunk] = []

    if "archive" in allowed:
        archive = root / "03-Archive"
        if archive.exists():
            for p in sorted(archive.rglob("*")):
                if p.suffix.lower() in (".md", ".txt", ".markdown") and p.is_file():
                    chunks.extend(
                        _chunks_from_markdown(
                            p, root, kind="archive", attribution="document"
                        )
                    )

    if "buffer" in allowed:
        buffer_dir = root / "05-Buffer"
        if buffer_dir.exists():
            for p in sorted(buffer_dir.rglob("*.md")):
                if p.is_file():
                    chunks.extend(
                        _chunks_from_markdown(
                            p, root, kind="buffer", attribution="document"
                        )
                    )

    if "discussion" in allowed:
        disc = root / "04-OutBox" / "discussions"
        if disc.exists():
            for p in sorted(disc.glob("*.md")):
                chunks.extend(_chunks_from_markdown(p, root, kind="discussion", attribution=DISCUSSION_ATTRIBUTION))

    if "outbox" in allowed:
        outbox = root / "04-OutBox"
        if outbox.exists():
            for p in sorted(outbox.glob("*.md")):
                if p.is_file():
                    chunks.extend(
                        _chunks_from_markdown(
                            p, root, kind="outbox", attribution="system"
                        )
                    )

    if "card_excerpt" in allowed:
        cards_dir = root / "01-Cards"
        if cards_dir.exists():
            for p in sorted(cards_dir.glob("*.md")):
                if p.name.startswith("_"):
                    continue
                meta, body = split_frontmatter(p.read_text(encoding="utf-8"))
                if not meta:
                    continue
                rel = _rel(root, p)
                cid = str(meta.get("id") or p.stem)
                origin = str(meta.get("origin") or "document")
                for heading, sec_body in _split_sections(body):
                    sec_anchor = f"{rel}#{heading}" if heading else rel
                    content = sec_body[:2000]
                    if not content.strip():
                        continue
                    chunks.append(
                        Chunk(
                            chunk_id=_chunk_id(rel, sec_anchor, content),
                            kind="card_excerpt",
                            path=rel,
                            anchor=sec_anchor,
                            attribution=origin,
                            body=content,
                            linked_cards=[cid],
                        )
                    )

    return chunks
