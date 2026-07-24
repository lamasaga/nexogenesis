from pathlib import Path

from nexogenesis.ingest import count_chars
from nexogenesis.ingest.chunker import (
    _split_text_by_paragraphs,
    build_compile_units,
)


def test_count_chars():
    assert count_chars("中文") == 2
    result = count_chars("hello world")
    assert isinstance(result, int)
    assert result > 0


def test_split_text_by_paragraphs():
    text = "\n\n".join([f"段落{i}" for i in range(10)])
    chunks = _split_text_by_paragraphs(text, max_chars=10)
    assert len(chunks) >= 1
    for c in chunks:
        assert count_chars(c) <= 10


def test_build_compile_units(tmp_path: Path):
    doc = tmp_path / "note.md"
    doc.write_text("第一段。\n\n第二段。\n\n第三段。", encoding="utf-8")
    units = build_compile_units([{"path": doc, "doc_type": "text"}], max_chars=100)
    assert len(units) == 1
    assert units[0]["source_path"] == doc
    assert "第一段" in units[0]["text"]
