from pathlib import Path

import pytest

from nexogenesis.ingest.ingest import (
    UnsupportedDocumentError,
    classify_file,
    predict_genre,
    scan_inbox,
)


def test_classify_file_text(tmp_path: Path):
    md = tmp_path / "a.md"
    md.write_text("hello", encoding="utf-8")
    assert classify_file(md) == "text"


def test_classify_file_unsupported(tmp_path: Path):
    p = tmp_path / "a.exe"
    p.write_bytes(b"x")
    with pytest.raises(UnsupportedDocumentError):
        classify_file(p)


def test_predict_genre_scrap():
    meta = {
        "char_count": 500,
        "dialogue_ratio": 0.0,
        "dialogue_lines": 0,
        "dialogue_speakers": 0,
        "academic_hits": 0,
        "heading_count": 0,
    }
    assert predict_genre(meta, "text") == "scrap"


def test_predict_genre_dialogue():
    meta = {
        "char_count": 5000,
        "dialogue_ratio": 0.5,
        "dialogue_lines": 5,
        "dialogue_speakers": 2,
        "academic_hits": 0,
        "heading_count": 0,
    }
    assert predict_genre(meta, "text") == "dialogue"


def test_predict_genre_paper():
    meta = {
        "char_count": 5000,
        "dialogue_ratio": 0.0,
        "dialogue_lines": 0,
        "dialogue_speakers": 0,
        "academic_hits": 2,
        "heading_count": 0,
    }
    assert predict_genre(meta, "text") == "paper"


def test_scan_inbox(tmp_path: Path):
    (tmp_path / "a.md").write_text("text", encoding="utf-8")
    (tmp_path / "b.txt").write_text("text", encoding="utf-8")
    docs = scan_inbox(tmp_path)
    assert len(docs) == 2
