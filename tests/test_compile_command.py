from pathlib import Path

from click.testing import CliRunner

from nexogenesis.commands.compile import compile_cmd
from nexogenesis.commands.init import init_cmd


def test_compile_generates_prompts(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    (tmp_path / "00-Inbox" / "note.md").write_text("这是一个测试文档。" * 20, encoding="utf-8")
    result = runner.invoke(compile_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    prompts = list((tmp_path / ".nexogenesis" / "tmp" / "compile").glob("*.md"))
    assert len(prompts) >= 1


def test_compile_plan(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    (tmp_path / "00-Inbox" / "note.md").write_text(
        "# 标题\n\n" + "这是一个测试文档，包含足够的字符数以避免被判定为零散材料。" * 50,
        encoding="utf-8",
    )
    result = runner.invoke(compile_cmd, ["--root", str(tmp_path), "--plan"])
    assert result.exit_code == 0, result.output
    assert "essay" in result.output


def test_compile_apply_writes_buffers_and_archives(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    inbox = tmp_path / "00-Inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "note.md").write_text("## 核心观点\n\n教学反馈应优先指出可操作差距。", encoding="utf-8")

    # 模拟 LLM response
    response = """
---
title: 教学反馈 claim
type: claim
source: note.md
---
教学反馈应优先指出可操作差距。
"""
    tmp_dir = tmp_path / ".nexogenesis" / "tmp" / "compile"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    (tmp_dir / "batch-001-essay-response.md").write_text(response, encoding="utf-8")

    result = runner.invoke(compile_cmd, ["--root", str(tmp_path), "--apply"])
    assert result.exit_code == 0, result.output
    buffers = list((tmp_path / "05-Buffer").rglob("*.md"))
    assert len(buffers) == 1
    assert not (inbox / "note.md").exists()
    assert (tmp_path / "03-Archive" / "note.md").exists()
