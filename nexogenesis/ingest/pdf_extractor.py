"""PDF 文本、目录与页码提取。"""

from pathlib import Path
from typing import Any

from nexogenesis.ingest import count_chars


class PdfExtractionError(RuntimeError):
    """PDF 提取失败。"""


def _fitz():
    try:
        import fitz
        return fitz
    except ImportError as e:  # pragma: no cover
        raise ImportError("PDF 处理需要 PyMuPDF，请运行：python -m pip install pymupdf") from e


def _estimate_chars_per_page(doc: Any, start: int = 0) -> float:
    """从 start 开始采样前 5 页估算平均每页等效中文字符数。"""
    samples = []
    try:
        for page in doc[start : start + 5]:
            try:
                text = page.get_text()
            except Exception as e:
                raise PdfExtractionError(f"提取页面文本失败: {e}") from e
            samples.append(count_chars(text))
    except Exception as e:
        if isinstance(e, PdfExtractionError):
            raise
        raise PdfExtractionError(f"估算每页字符数失败: {e}") from e

    return sum(samples) / len(samples) if samples else 500.0


def _split_by_page_ranges(
    doc: Any,
    max_chars: int,
    start: int = 0,
    end: int | None = None,
) -> list[dict]:
    """按页码范围切分，尽量让每段字数 ≤ max_chars。"""
    if end is None:
        end = len(doc)
    end = min(end, len(doc))
    start = max(0, start)

    chars_per_page = _estimate_chars_per_page(doc, start)
    pages_per_chunk = max(1, int(max_chars / max(chars_per_page, 1)))

    chunks = []
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + pages_per_chunk, end)
        text_parts = []
        for page in doc[cursor:chunk_end]:
            try:
                text_parts.append(page.get_text())
            except Exception as e:
                raise PdfExtractionError(f"提取页面文本失败: {e}") from e
        text = "\n".join(text_parts)
        chars = count_chars(text)
        if chars > max_chars and pages_per_chunk > 1:
            pages_per_chunk = max(1, pages_per_chunk // 2)
            continue
        chunks.append({
            "title": f"页码 {cursor + 1}-{chunk_end}",
            "page_range": f"{cursor + 1}-{chunk_end}",
            "text": text,
            "char_count": chars,
        })
        pages_in_chunk = chunk_end - cursor
        cursor = chunk_end
        if chars > 0:
            actual_chars_per_page = chars / pages_in_chunk
            pages_per_chunk = max(1, int(max_chars / max(actual_chars_per_page, 1)))
    return chunks


def select_toc_window_entries(toc: list) -> list[tuple[int, int, str, int]]:
    """从 PDF TOC 选出阅读窗条目。

    策略：若存在更细目录（子节），跳过「下面还有子节」的粗章，
    优先以小节/小标题为窗；仅当某章无子节时才用该章本身。

    返回 [(toc_index, level, title, page), ...]
    """
    if not toc:
        return []
    selected: list[tuple[int, int, str, int]] = []
    for i, entry in enumerate(toc):
        level, title, page = entry[0], entry[1], entry[2]
        next_level = toc[i + 1][0] if i + 1 < len(toc) else None
        has_child = next_level is not None and next_level > level
        if has_child:
            # 粗章/父标题：留给子节开窗
            continue
        selected.append((i, int(level), str(title), int(page)))
    # 极端情况：全部被跳过（异常 TOC）→ 回退用全部条目
    if not selected:
        for i, entry in enumerate(toc):
            selected.append((i, int(entry[0]), str(entry[1]), int(entry[2])))
    return selected


def extract_pdf_toc_chunks(path: Path, max_chars: int = 30000) -> list[dict]:
    """提取 PDF 文本并按目录/页码切分为编译单元（优先小节窗）。"""
    if max_chars <= 0:
        raise ValueError("max_chars 必须大于 0")
    if not path.is_file():
        raise PdfExtractionError(f"PDF 路径不存在或不是文件: {path}")

    try:
        with _fitz().open(path) as doc:
            try:
                toc = doc.get_toc()
            except Exception as e:
                raise PdfExtractionError(f"无法读取 PDF 目录: {e}") from e

            chunks: list[dict] = []
            if toc:
                windows = select_toc_window_entries(toc)
                for wi, (toc_i, _level, title, page) in enumerate(windows):
                    page = max(1, page)
                    if wi + 1 < len(windows):
                        end_page = windows[wi + 1][3]
                    elif toc_i + 1 < len(toc):
                        end_page = toc[toc_i + 1][2]
                    else:
                        end_page = len(doc) + 1
                    end_page = max(page, int(end_page))

                    start_idx = max(0, page - 1)
                    end_idx = max(start_idx, min(end_page - 1, len(doc)))

                    text_parts = []
                    for page_obj in doc[start_idx:end_idx]:
                        try:
                            text_parts.append(page_obj.get_text())
                        except Exception as e:
                            raise PdfExtractionError(f"提取页面文本失败: {e}") from e
                    text = "\n".join(text_parts)

                    if count_chars(text) > max_chars:
                        sub_chunks = _split_by_page_ranges(doc, max_chars, start_idx, end_idx)
                        for sc in sub_chunks:
                            sc["title"] = f"{title} / {sc['title']}"
                            sc["section"] = title
                        chunks.extend(sub_chunks)
                    else:
                        chunks.append({
                            "title": title,
                            "section": title,
                            "page_range": f"{page}-{end_page - 1}",
                            "text": text,
                        })
            else:
                chunks = _split_by_page_ranges(doc, max_chars)
    except Exception as e:
        if isinstance(e, PdfExtractionError):
            raise
        raise PdfExtractionError(f"提取 PDF 失败: {e}") from e

    result = []
    for c in chunks:
        try:
            c["char_count"] = count_chars(c["text"])
        except Exception as e:
            raise PdfExtractionError(f"计算字符数失败: {e}") from e
        if c["text"]:
            result.append(c)
    return result
