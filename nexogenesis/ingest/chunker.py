"""将原始文档切分为编译单元。"""

import re
from pathlib import Path

from nexogenesis.ingest import (
    CHINESE_CHAR_COST_NUM,
    ENGLISH_WORD_COST_NUM,
    WORD_RE,
    count_chars,
)
from nexogenesis.ingest.ingest import DIALOGUE_LINE_RE


SENTENCE_END_RE = re.compile(r"([。.?!？！])")


def _flush_current(current: list[str], chunks: list[str]) -> list[str]:
    if current:
        chunks.append("\n\n".join(current))
    return []


def _ceil_half(total: int) -> int:
    return (total + 1) // 2


def _tokenize_for_count(text: str) -> list[tuple[str, int]]:
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        m = WORD_RE.match(text, i)
        if m:
            word = m.group(0)
            tokens.append((word, ENGLISH_WORD_COST_NUM))
            i = m.end()
        else:
            ch = text[i]
            cost = CHINESE_CHAR_COST_NUM if "\u4e00" <= ch <= "\u9fff" else 0
            tokens.append((ch, cost))
            i += 1
    return tokens


def _split_long_sentence(sentence: str, max_chars: int) -> list[str]:
    if count_chars(sentence) <= max_chars:
        return [sentence]

    chunks = []
    current = []
    current_cost_num = 0

    for token, token_cost_num in _tokenize_for_count(sentence):
        if current and _ceil_half(current_cost_num + token_cost_num) > max_chars:
            chunks.append("".join(current))
            current = []
            current_cost_num = 0
        current.append(token)
        current_cost_num += token_cost_num

    if current:
        chunks.append("".join(current))
    return chunks


def _split_text_by_paragraphs(text: str, max_chars: int) -> list[str]:
    if max_chars <= 0:
        raise ValueError("max_chars 必须为正数")
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = []
    current_len = 0

    for para in paragraphs:
        para_len = count_chars(para)
        if para_len > max_chars:
            current = _flush_current(current, chunks)
            current_len = 0

            parts = SENTENCE_END_RE.split(para)
            sentences = []
            for i in range(0, len(parts) - 1, 2):
                sentence = parts[i] + parts[i + 1]
                if sentence.strip():
                    sentences.append(sentence)
            if len(parts) % 2 == 1 and parts[-1].strip():
                sentences.append(parts[-1].strip())

            for sentence in sentences:
                s_len = count_chars(sentence)
                if s_len > max_chars:
                    current = _flush_current(current, chunks)
                    current_len = 0
                    for sub in _split_long_sentence(sentence, max_chars):
                        sub_len = count_chars(sub)
                        if current_len + sub_len > max_chars and current:
                            current = _flush_current(current, chunks)
                            current_len = 0
                        current.append(sub)
                        current_len += sub_len
                    continue

                if current_len + s_len > max_chars and current:
                    current = _flush_current(current, chunks)
                    current_len = 0

                current.append(sentence)
                current_len += s_len
            continue

        if current_len + para_len > max_chars and current:
            current = _flush_current(current, chunks)
            current_len = 0

        current.append(para)
        current_len += para_len

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def _split_dialogue_by_turns(text: str, max_chars: int) -> list[str]:
    if max_chars <= 0:
        raise ValueError("max_chars 必须为正数")
    lines = text.split("\n")

    turns = []
    current: list[str] = []
    for line in lines:
        if DIALOGUE_LINE_RE.match(line.strip()) and current:
            turns.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        turns.append("\n".join(current))

    chunks = []
    buf: list[str] = []
    buf_len = 0
    for turn in turns:
        turn_len = count_chars(turn)
        if turn_len > max_chars:
            if buf:
                chunks.append("\n".join(buf))
                buf, buf_len = [], 0
            chunks.extend(_split_text_by_paragraphs(turn, max_chars))
            continue
        if buf_len + turn_len > max_chars and buf:
            chunks.append("\n".join(buf))
            buf, buf_len = [], 0
        buf.append(turn)
        buf_len += turn_len
    if buf:
        chunks.append("\n".join(buf))

    return [c for c in chunks if c.strip()]


def build_compile_units(
    docs: list[dict],
    max_chars: int = 30000,
    genres: dict | None = None,
) -> list[dict]:
    """将扫描得到的文档列表转换为编译单元队列。"""
    if max_chars <= 0:
        raise ValueError("max_chars 必须为正数")
    units = []
    genres = genres or {}

    for doc in docs:
        path: Path = doc["path"]
        doc_type = doc["doc_type"]
        source_key = doc.get("name") or path.name
        genre = genres.get(source_key) or genres.get(path.name)

        if doc_type == "text":
            text = path.read_text(encoding="utf-8")
            if genre == "dialogue":
                chunks = _split_dialogue_by_turns(text, max_chars)
            else:
                chunks = _split_text_by_paragraphs(text, max_chars)
            for idx, chunk_text in enumerate(chunks):
                units.append({
                    "unit_id": f"{path.stem}-{idx + 1:03d}",
                    "source_path": path,
                    "source_key": source_key,
                    "doc_type": "text",
                    "title": path.name,
                    "page_range": "",
                    "section": f"片段 {idx + 1}/{len(chunks)}" if len(chunks) > 1 else "",
                    "char_count": count_chars(chunk_text),
                    "text": chunk_text,
                    "archivable": False,
                    "genre": genre,
                })

        elif doc_type == "pdf":
            from nexogenesis.ingest.pdf_extractor import extract_pdf_toc_chunks
            pdf_chunks = extract_pdf_toc_chunks(path, max_chars=max_chars)
            for idx, chunk in enumerate(pdf_chunks):
                units.append({
                    "unit_id": f"{path.stem}-{idx + 1:03d}",
                    "source_path": path,
                    "source_key": source_key,
                    "doc_type": "pdf",
                    "title": chunk["title"],
                    "page_range": chunk["page_range"],
                    "section": "",
                    "char_count": chunk["char_count"],
                    "text": chunk["text"],
                    "archivable": False,
                    "genre": genre,
                })

        else:
            raise ValueError(f"未知文档类型: {doc_type}")

    return units
