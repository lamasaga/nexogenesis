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


HEADING_LINE_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)

# 体裁 → 是否优先按标题开窗（图书/长文/通用带标题稿）
HEADING_WINDOW_GENRES = frozenset({"book", "essay", "generic", None})


def split_text_by_headings(
    text: str,
    max_chars: int,
    *,
    prefer_min_level: int = 2,
) -> list[dict]:
    """按 Markdown 标题切阅读窗；返回 [{title, section, text}, ...]。

    优先以 ## / ###（level>=prefer_min_level）为窗；若只有 # 或无标题则回退。
    超长窗再按段落切开，标题保留在 section 前缀。
    """
    if max_chars <= 0:
        raise ValueError("max_chars 必须为正数")
    matches = list(HEADING_LINE_RE.finditer(text or ""))
    if not matches:
        return [{"title": "", "section": "", "text": t} for t in _split_text_by_paragraphs(text, max_chars)]

    # 统计各级标题
    levels = [len(m.group(1)) for m in matches]
    use_level = prefer_min_level
    if not any(lv >= prefer_min_level for lv in levels):
        use_level = min(levels)

    # 选窗：跳过「后面紧跟更细标题」的粗标题（同 PDF TOC 策略）
    window_idxs: list[int] = []
    for i, m in enumerate(matches):
        lv = len(m.group(1))
        if lv < use_level:
            continue
        next_lv = len(matches[i + 1].group(1)) if i + 1 < len(matches) else None
        if next_lv is not None and next_lv > lv:
            continue
        window_idxs.append(i)

    if not window_idxs:
        window_idxs = [i for i, m in enumerate(matches) if len(m.group(1)) >= use_level]
    if not window_idxs:
        window_idxs = list(range(len(matches)))

    sections: list[dict] = []
    # 文首无标题的前缀
    first_start = matches[window_idxs[0]].start()
    prefix = text[:first_start].strip()
    if prefix:
        sections.append({"title": "(文首)", "section": "(文首)", "text": prefix})

    for wi, mi in enumerate(window_idxs):
        m = matches[mi]
        title = m.group(2).strip()
        start = m.start()
        if wi + 1 < len(window_idxs):
            end = matches[window_idxs[wi + 1]].start()
        else:
            end = len(text)
        body = text[start:end].strip()
        if not body:
            continue
        if count_chars(body) <= max_chars:
            sections.append({"title": title, "section": title, "text": body})
        else:
            for j, part in enumerate(_split_text_by_paragraphs(body, max_chars)):
                suffix = f" / 续{j + 1}" if j else ""
                sections.append({
                    "title": f"{title}{suffix}",
                    "section": title,
                    "text": part,
                })
    return sections or [{"title": "", "section": "", "text": text}]


def _text_units_for_genre(text: str, genre: str | None, max_chars: int) -> list[dict]:
    """按体裁选择文本切窗策略；返回带 title/section/text 的窗列表。"""
    if genre == "dialogue":
        return [
            {"title": f"对话片段 {i + 1}", "section": f"对话片段 {i + 1}", "text": t}
            for i, t in enumerate(_split_dialogue_by_turns(text, max_chars))
        ]
    if genre == "scrap":
        return [
            {"title": f"片段 {i + 1}", "section": f"片段 {i + 1}", "text": t}
            for i, t in enumerate(_split_text_by_paragraphs(text, max_chars))
        ]
    if genre == "paper":
        # 论文：有小标题则按标题；否则少窗（大段落堆叠）
        if HEADING_LINE_RE.search(text or ""):
            return split_text_by_headings(text, max_chars, prefer_min_level=2)
        return [
            {"title": f"片段 {i + 1}", "section": f"片段 {i + 1}", "text": t}
            for i, t in enumerate(_split_text_by_paragraphs(text, max_chars))
        ]
    # book / essay / generic / 未知：优先标题窗
    if genre in HEADING_WINDOW_GENRES or genre in ("book", "essay", "generic"):
        if HEADING_LINE_RE.search(text or ""):
            return split_text_by_headings(text, max_chars, prefer_min_level=2)
    return [
        {"title": f"片段 {i + 1}", "section": f"片段 {i + 1}", "text": t}
        for i, t in enumerate(_split_text_by_paragraphs(text, max_chars))
    ]


def build_compile_units(
    docs: list[dict],
    max_chars: int = 30000,
    genres: dict | None = None,
) -> list[dict]:
    """将扫描得到的文档列表转换为编译单元队列。

    Harness 负责按体裁开「阅读窗」；窗内切几块 Buffer 由 LLM 判断。
    """
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
            windows = _text_units_for_genre(text, genre, max_chars)
            for idx, win in enumerate(windows):
                units.append({
                    "unit_id": f"{path.stem}-{idx + 1:03d}",
                    "source_path": path,
                    "source_key": source_key,
                    "doc_type": "text",
                    "title": win.get("title") or path.name,
                    "page_range": "",
                    "section": win.get("section") or "",
                    "char_count": count_chars(win["text"]),
                    "text": win["text"],
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
                    "section": chunk.get("section") or chunk.get("title") or "",
                    "char_count": chunk["char_count"],
                    "text": chunk["text"],
                    "archivable": False,
                    "genre": genre,
                })

        else:
            raise ValueError(f"未知文档类型: {doc_type}")

    return units
