from pathlib import Path

from click.testing import CliRunner

from nexogenesis.commands.init import init_cmd
from nexogenesis.ingest.batch_runner import (
    build_batches,
    check_response_file,
    parse_llm_buffers,
    write_buffer,
)


def test_build_batches_respects_max_chars():
    units = [
        {"char_count": 20000, "text": "a", "genre": "essay", "source_path": "a.md"},
        {"char_count": 20000, "text": "b", "genre": "essay", "source_path": "b.md"},
    ]
    batches = build_batches(units, max_chars=30000)
    assert len(batches) == 2


def test_build_batches_limits_scrap_docs():
    units = [
        {"char_count": 100, "text": "a", "genre": "scrap", "source_path": Path(f"{i}.md")}
        for i in range(5)
    ]
    batches = build_batches(units, max_chars=10000)
    assert len(batches) == 2
    assert all(len({str(u["source_path"]) for u in b}) <= 3 for b in batches)


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


def test_parse_llm_buffers_crlf_and_table_dividers():
    raw = (
        "---\r\n"
        "title: 表\r\n"
        "role: artifact-table\r\n"
        'source: "a.pdf / Table 1: scores"\r\n'
        "---\r\n"
        "### 标题与编号\r\n\r\n"
        "表1\r\n\r\n"
        "### 内容转写\r\n\r\n"
        "| a | b |\r\n"
        "| --- | --- |\r\n"
        "| 1 | 2 |\r\n\r\n"
        "---\r\n"
        "title: 主张\r\n"
        "role: meaning-unit\r\n"
        "source: a.pdf\r\n"
        "---\r\n"
        "### 核心表达\r\n\r\n"
        "点\r\n\r\n"
        "### 依据与细节\r\n\r\n"
        "原文未提及：无\r\n\r\n"
        "### 限制与边界\r\n\r\n"
        "原文未提及：无\r\n\r\n"
        "### 原文摘录\r\n\r\n"
        "> x\r\n"
    )
    buffers = parse_llm_buffers(raw, "default")
    assert len(buffers) == 2
    assert buffers[0]["role"] == "artifact-table"
    assert "| --- | --- |" in buffers[0]["body"]
    assert buffers[1]["role"] == "meaning-unit"


def test_check_response_file_soft_slot_warning(tmp_path: Path):
    p = tmp_path / "batch-001-scrap-response.md"
    p.write_text(
        "---\n"
        "title: 薄\n"
        "role: meaning-unit\n"
        "source: s.md\n"
        "---\n"
        "只有一句话，没有槽标题。\n",
        encoding="utf-8",
    )
    buffers, hard, soft = check_response_file(p, strict_body=False)
    assert len(buffers) == 1
    assert hard == []
    assert soft
    _, hard2, _ = check_response_file(p, strict_body=True)
    assert hard2
