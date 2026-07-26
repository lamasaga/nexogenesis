from pathlib import Path

from click.testing import CliRunner

from nexogenesis.commands.init import init_cmd
from nexogenesis.ingest.batch_runner import build_batches, parse_llm_buffers, write_buffer


def test_build_batches_respects_max_chars():
    units = [
        {"char_count": 20000, "text": "a"},
        {"char_count": 20000, "text": "b"},
    ]
    batches = build_batches(units, max_chars=30000)
    assert len(batches) == 2


def test_parse_llm_buffers():
    raw = """
---
title: 测试
role: meaning-unit
source: s1
proposed_card_type: claim
---
正文1

---
title: 测试2
role: tension
source: s2
---
正文2
"""
    buffers = parse_llm_buffers(raw, "default")
    assert len(buffers) == 2
    assert buffers[0]["role"] == "meaning-unit"
    assert buffers[0]["proposed_card_type"] == "claim"
    assert buffers[1]["role"] == "tension"


def test_parse_llm_buffers_legacy_type_becomes_meaning_unit():
    raw = """
---
title: 测试
type: claim
source: s1
---
正文
"""
    buffers = parse_llm_buffers(raw, "default")
    assert buffers[0]["role"] == "meaning-unit"
    assert buffers[0]["proposed_card_type"] == "claim"


def test_parse_llm_buffers_invalid_role_fallback():
    raw = """
---
title: 测试
role: notion
source: s1
---
正文
"""
    buffers = parse_llm_buffers(raw, "default")
    assert buffers[0]["role"] == "meaning-unit"


def test_write_buffer(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    buffer_dir = tmp_path / "05-Buffer"
    buf = {
        "title": "测试碎片",
        "role": "meaning-unit",
        "source": "test",
        "body": "这是正文",
    }
    path = write_buffer(buf, "meaning-unit", buffer_dir)
    assert path.exists()
    assert "meaning-unit" in str(path)
    text = path.read_text(encoding="utf-8")
    assert "测试碎片" in text
    assert "role: meaning-unit" in text
    assert "这是正文" in text
