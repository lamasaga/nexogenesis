"""阅读窗：标题切分与 PDF TOC 选窗。"""

from pathlib import Path

from nexogenesis.ingest.batch_runner import build_batches, max_units_for_genre
from nexogenesis.ingest.chunker import build_compile_units, split_text_by_headings
from nexogenesis.ingest.pdf_extractor import (
    filter_content_toc_windows,
    is_front_matter_title,
    select_toc_window_entries,
    toc_is_front_matter_only,
)


def test_select_toc_skips_parent_with_children():
    toc = [
        [1, "第一章", 1],
        [2, "1.1 开篇", 1],
        [2, "1.2 展开", 10],
        [1, "第二章", 20],
        [2, "2.1 细节", 20],
    ]
    wins = select_toc_window_entries(toc)
    titles = [t for _, _, t, _ in wins]
    assert "第一章" not in titles
    assert "第二章" not in titles
    assert "1.1 开篇" in titles
    assert "1.2 展开" in titles
    assert "2.1 细节" in titles


def test_select_toc_keeps_chapter_without_children():
    toc = [
        [1, "第一章", 1],
        [1, "第二章", 50],
    ]
    wins = select_toc_window_entries(toc)
    titles = [t for _, _, t, _ in wins]
    assert titles == ["第一章", "第二章"]


def test_front_matter_titles_detected():
    assert is_front_matter_title("Book Cover")
    assert is_front_matter_title("Title")
    assert is_front_matter_title("Copyright")
    assert is_front_matter_title("Contents")
    assert is_front_matter_title("目录")
    assert not is_front_matter_title("第一章 导论")
    assert not is_front_matter_title("1.2 Monetary Policy")


def test_toc_front_matter_only_like_user_pdf():
    toc = [
        [1, "Book Cover", 1],
        [1, "Title", 2],
        [1, "Copyright", 3],
        [1, "Contents", 4],
    ]
    assert toc_is_front_matter_only(toc, page_count=342)
    wins = filter_content_toc_windows(select_toc_window_entries(toc))
    assert wins == []


def test_toc_real_chapters_not_front_only():
    toc = [
        [1, "Book Cover", 1],
        [1, "Contents", 3],
        [1, "Chapter 1 Introduction", 12],
        [1, "Chapter 2 Analysis", 40],
    ]
    assert not toc_is_front_matter_only(toc, page_count=200)
    wins = filter_content_toc_windows(select_toc_window_entries(toc))
    titles = [t for _, _, t, _ in wins]
    assert "Book Cover" not in titles
    assert "Contents" not in titles
    assert "Chapter 1 Introduction" in titles


def test_split_text_by_headings_prefers_h2():
    text = """# 大书

## 第一节 甲

　　甲的内容很长，有机制说明。

## 第二节 乙

　　乙的内容也有依据。

### 2.1 子节

　　子节细节。
"""
    wins = split_text_by_headings(text, max_chars=50000)
    titles = [w["title"] for w in wins]
    assert "第一节 甲" in titles
    assert "2.1 子节" in titles


def test_book_batch_one_unit_per_prompt(tmp_path: Path):
    assert max_units_for_genre("book") == 1
    p = tmp_path / "book.md"
    p.write_text("# 书\n\n## A\n\n" + ("甲" * 100) + "\n\n## B\n\n" + ("乙" * 100), encoding="utf-8")
    units = build_compile_units(
        [{"path": p, "doc_type": "text", "name": "book.md"}],
        max_chars=10000,
        genres={"book.md": "book"},
    )
    assert len(units) >= 2
    batches = build_batches(units, max_chars=10000)
    assert all(len(b) == 1 for b in batches)
