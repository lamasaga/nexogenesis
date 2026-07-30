"""PDF 文本、目录与页码提取。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from nexogenesis.ingest import count_chars


class PdfExtractionError(RuntimeError):
    """PDF 提取失败。"""


# 常见扉页/前页书签名（多语言）；命中则不当正文阅读窗
_FRONT_MATTER_RE = re.compile(
    r"(?i)^("
    r"book\s*cover|cover|title(\s*page)?|half[- ]?title|copyright|"
    r"contents|table\s*of\s*contents|toc|"
    r"封面|书名页|扉页|版权|版权页|目录|目次|献词|题词|出版说明|"
    r"about\s+the\s+author|作者简介|插图目录|图表目录"
    r")$"
)


def _fitz():
    try:
        import fitz
        return fitz
    except ImportError as e:  # pragma: no cover
        raise ImportError("PDF 处理需要 PyMuPDF，请运行：python -m pip install pymupdf") from e


def is_front_matter_title(title: str) -> bool:
    """判断 TOC 标题是否像封面/版权/目录等前页。"""
    t = (title or "").strip()
    if not t:
        return True
    if _FRONT_MATTER_RE.match(t):
        return True
    # 软匹配：整标题很短且含关键词
    low = t.lower()
    for kw in ("copyright", "contents", "封面", "目录", "版权", "书名"):
        if kw in low or kw in t:
            if len(t) <= 24:
                return True
    return False


def toc_is_front_matter_only(toc: list, page_count: int) -> bool:
    """TOC 是否几乎只有前页、无法支撑全书小节开窗。"""
    if not toc:
        return True
    if page_count <= 0:
        return True
    if all(is_front_matter_title(str(e[1])) for e in toc):
        return True
    max_page = max(int(e[2]) for e in toc)
    # 长书：全部书签挤在最前面一小段 → 视为无效正文 TOC
    if page_count >= 40 and max_page <= max(15, int(page_count * 0.08)):
        return True
    # 书签很少且全在前部
    if len(toc) <= 6 and page_count >= 80 and max_page <= 20:
        return True
    return False


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
            continue
        selected.append((i, int(level), str(title), int(page)))
    if not selected:
        for i, entry in enumerate(toc):
            selected.append((i, int(entry[0]), str(entry[1]), int(entry[2])))
    return selected


def filter_content_toc_windows(
    windows: list[tuple[int, int, str, int]],
) -> list[tuple[int, int, str, int]]:
    """去掉扉页类窗，避免浪费 compile prompt。"""
    return [w for w in windows if not is_front_matter_title(w[2])]


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


def find_body_start_page(doc: Any, *, hint_page: int = 1, min_chars: int = 120) -> int:
    """找到正文起始页（0-based index）。

    从 hint 附近向前扫描，跳过几乎无字的扫描页/空白页。
    """
    n = len(doc)
    if n <= 0:
        return 0
    start = max(0, min(n - 1, max(0, hint_page - 1)))
    # 先从 hint 起找；找不到再从头找
    for idx in list(range(start, n)) + list(range(0, start)):
        try:
            text = doc[idx].get_text() or ""
        except Exception as e:
            raise PdfExtractionError(f"提取页面文本失败: {e}") from e
        if count_chars(text) >= min_chars:
            return idx
    return start


def _split_by_page_ranges(
    doc: Any,
    max_chars: int,
    start: int = 0,
    end: int | None = None,
    *,
    title_prefix: str = "",
) -> list[dict]:
    """按页码范围切分，尽量让每段字数 ≤ max_chars。"""
    if end is None:
        end = len(doc)
    end = min(end, len(doc))
    start = max(0, start)
    if start >= end:
        return []

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
        # 跳过几乎空白的窗（扫描件空页等）
        if chars < 40:
            cursor = chunk_end
            continue
        page_label = f"页码 {cursor + 1}-{chunk_end}"
        title = f"{title_prefix} / {page_label}" if title_prefix else page_label
        chunks.append({
            "title": title,
            "section": title_prefix or page_label,
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


def _chunks_from_toc_windows(
    doc: Any,
    toc: list,
    windows: list[tuple[int, int, str, int]],
    max_chars: int,
) -> list[dict]:
    chunks: list[dict] = []
    page_count = len(doc)

    # 首个正文窗之前若有大段无书签正文，按页补窗
    first_page = max(1, int(windows[0][3]))
    body_start = find_body_start_page(doc, hint_page=1)
    if first_page - 1 - body_start >= 3:
        chunks.extend(
            _split_by_page_ranges(
                doc, max_chars, body_start, first_page - 1, title_prefix="文首"
            )
        )

    for wi, (toc_i, _level, title, page) in enumerate(windows):
        page = max(1, int(page))
        if wi + 1 < len(windows):
            end_page = int(windows[wi + 1][3])
        elif toc_i + 1 < len(toc):
            end_page = int(toc[toc_i + 1][2])
        else:
            end_page = page_count + 1
        end_page = max(page, end_page)

        start_idx = max(0, page - 1)
        end_idx = max(start_idx, min(end_page - 1, page_count))

        text_parts = []
        for page_obj in doc[start_idx:end_idx]:
            try:
                text_parts.append(page_obj.get_text())
            except Exception as e:
                raise PdfExtractionError(f"提取页面文本失败: {e}") from e
        text = "\n".join(text_parts)

        if count_chars(text) > max_chars:
            sub = _split_by_page_ranges(
                doc, max_chars, start_idx, end_idx, title_prefix=title
            )
            chunks.extend(sub)
        elif count_chars(text) >= 40:
            chunks.append({
                "title": title,
                "section": title,
                "page_range": f"{page}-{end_page - 1}",
                "text": text,
            })

    # 最后一书签未覆盖到书末时补页窗
    last_end = 0
    if chunks:
        # page_range 形如 "12-20"
        try:
            last_end = int(str(chunks[-1].get("page_range", "0")).split("-")[-1])
        except ValueError:
            last_end = 0
    if last_end < page_count:
        chunks.extend(
            _split_by_page_ranges(
                doc, max_chars, last_end, page_count, title_prefix="续文"
            )
        )
    return chunks


def extract_pdf_toc_chunks(path: Path, max_chars: int = 30000) -> list[dict]:
    """提取 PDF 文本并切分为编译单元。

    - TOC 有效：按小节开窗，跳过封面/版权/目录等扉页书签；
    - TOC 仅前页或缺失：从正文起始页起按字数/页码开窗（避免 4 个 prompt 全是封面）。
    """
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

            page_count = len(doc)
            if toc_is_front_matter_only(toc, page_count):
                hint = max((int(e[2]) for e in toc), default=1) if toc else 1
                # 目录页之后更可能是正文
                body_start = find_body_start_page(doc, hint_page=hint + 1)
                chunks = _split_by_page_ranges(doc, max_chars, body_start)
            else:
                windows = filter_content_toc_windows(select_toc_window_entries(toc))
                if not windows:
                    body_start = find_body_start_page(doc, hint_page=1)
                    chunks = _split_by_page_ranges(doc, max_chars, body_start)
                else:
                    chunks = _chunks_from_toc_windows(doc, toc, windows, max_chars)
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
        if c.get("text") and c["char_count"] >= 40:
            result.append(c)
    return result
