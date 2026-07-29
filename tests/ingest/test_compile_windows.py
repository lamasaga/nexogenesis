"""阅读窗：标题切分与 PDF TOC 选窗。"""

from nexogenesis.ingest.chunker import split_text_by_headings, build_compile_units
from nexogenesis.ingest.pdf_extractor import select_toc_window_entries
from nexogenesis.ingest.batch_runner import build_batches, max_units_for_genre
from pathlib import Path


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
    assert "第二节 乙" not in titles or "2.1 子节" in titles
    # 第二节有子节时应跳过「第二节 乙」，只留 2.1
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
