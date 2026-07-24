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
type: claim
source: s1
---
正文1

---
title: 测试2
type: model
source: s2
---
正文2
"""
    buffers = parse_llm_buffers(raw, "default")
    assert len(buffers) == 2
    assert buffers[0]["type"] == "claim"
    assert buffers[1]["type"] == "model"


def test_parse_llm_buffers_invalid_type_fallback():
    raw = """
---
title: 测试
type: notion
source: s1
---
正文
"""
    buffers = parse_llm_buffers(raw, "default")
    assert buffers[0]["type"] == "claim"


def test_write_buffer(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    buffer_dir = tmp_path / "05-Buffer"
    buf = {
        "title": "测试碎片",
        "type": "claim",
        "source": "test",
        "body": "这是正文",
    }
    path = write_buffer(buf, "claim", buffer_dir)
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "测试碎片" in text
    assert "这是正文" in text
