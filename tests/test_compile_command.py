from pathlib import Path

from click.testing import CliRunner

from nexogenesis.commands.compile import compile_cmd
from nexogenesis.commands.init import init_cmd
from nexogenesis.ingest.batch_runner import build_batches
from nexogenesis.ingest.compile_planner import (
    InventoryItem,
    resolve_policy,
    select_wave,
)


def test_compile_generates_prompts(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    (tmp_path / "00-Inbox" / "note.md").write_text("这是一个测试文档。" * 20, encoding="utf-8")
    result = runner.invoke(compile_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    prompts = list((tmp_path / ".nexogenesis" / "tmp" / "compile").glob("*-prompt.md"))
    assert len(prompts) >= 1
    assert (tmp_path / ".nexogenesis" / "tmp" / "compile" / "wave-manifest.json").exists()


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
    assert "分波计划" in result.output


def test_compile_wave_limits_prompts(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    inbox = tmp_path / "00-Inbox"
    for i in range(12):
        (inbox / f"scrap-{i:02d}.md").write_text(f"短笔记 {i} 内容。" * 5, encoding="utf-8")

    result = runner.invoke(
        compile_cmd,
        ["--root", str(tmp_path), "--wave-prompts", "2", "--wave-docs", "3", "--max-chars", "8000"],
    )
    assert result.exit_code == 0, result.output
    prompts = list((tmp_path / ".nexogenesis" / "tmp" / "compile").glob("*-prompt.md"))
    assert len(prompts) <= 2
    assert "本波" in result.output
    # 未处理文档仍在 Inbox
    assert len(list(inbox.glob("*.md"))) == 12


def test_compile_apply_writes_buffers_and_archives(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    inbox = tmp_path / "00-Inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "note.md").write_text("## 核心观点\n\n教学反馈应优先指出可操作差距。", encoding="utf-8")

    # 先生成 prompt + manifest
    gen = runner.invoke(compile_cmd, ["--root", str(tmp_path)])
    assert gen.exit_code == 0, gen.output

    response = """
---
title: 教学反馈
role: meaning-unit
source: "note.md"
proposed_card_type: claim
---
### 核心表达

　　教学反馈应优先指出可操作差距。

### 依据与细节

　　原文未提及：测试材料未展开依据。

### 限制与边界

　　原文未提及：测试材料未讨论边界。

### 原文摘录

> 教学反馈应优先指出可操作差距。
"""
    tmp_dir = tmp_path / ".nexogenesis" / "tmp" / "compile"
    prompts = list(tmp_dir.glob("batch-*-prompt.md"))
    assert prompts
    prefix = prompts[0].name.replace("-prompt.md", "")
    (tmp_dir / f"{prefix}-response.md").write_text(response, encoding="utf-8")

    result = runner.invoke(compile_cmd, ["--root", str(tmp_path), "--apply"])
    assert result.exit_code == 0, result.output
    buffers = list((tmp_path / "05-Buffer").rglob("*.md"))
    assert len(buffers) == 1
    assert "meaning-unit" in str(buffers[0])
    assert not (inbox / "note.md").exists()
    assert (tmp_path / "03-Archive" / "note.md").exists()


def test_select_wave_prefers_scraps_and_caps(tmp_path: Path):
    items = []
    for i in range(8):
        p = tmp_path / f"s{i}.md"
        p.write_text("短。" * 20, encoding="utf-8")
        items.append(
            InventoryItem(path=p, doc_type="text", genre="scrap", char_count=40, name=p.name)
        )
    book = tmp_path / "book.md"
    book.write_text("# 章\n\n" + ("长文。" * 5000) + "\n", encoding="utf-8")
    items.append(
        InventoryItem(path=book, doc_type="text", genre="book", char_count=15000, name=book.name)
    )
    policy = resolve_policy(wave_prompts=2, wave_docs=3, max_chars=5000)
    wave = select_wave(items, policy, {"sources": {}})
    assert all(i.genre == "scrap" for i in wave.selected)
    assert len(wave.batches) <= 2
    assert len(wave.selected) <= 3


def test_build_batches_does_not_mix_genres():
    units = [
        {"char_count": 100, "text": "a", "genre": "scrap", "source_path": Path("a.md")},
        {"char_count": 100, "text": "b", "genre": "paper", "source_path": Path("b.md")},
    ]
    batches = build_batches(units, max_chars=10000)
    assert len(batches) == 2


GOOD_RESPONSE = """
---
title: 教学反馈
role: meaning-unit
source: "note.md"
proposed_card_type: claim
---
### 核心表达

　　教学反馈应优先指出可操作差距。

### 依据与细节

　　原文未提及：测试材料未展开依据。

### 限制与边界

　　原文未提及：测试材料未讨论边界。

### 原文摘录

> 教学反馈应优先指出可操作差距。
"""

BAD_RESPONSE = """
---
title: Broken
role: meaning-unit
source: note.md / Section: Has Colon Without Quotes
---
no slots
"""


def test_compile_check_responses(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    (tmp_path / "00-Inbox" / "note.md").write_text("短笔记内容。" * 10, encoding="utf-8")
    gen = runner.invoke(compile_cmd, ["--root", str(tmp_path)])
    assert gen.exit_code == 0, gen.output
    tmp_dir = tmp_path / ".nexogenesis" / "tmp" / "compile"
    prompts = list(tmp_dir.glob("batch-*-prompt.md"))
    prefix = prompts[0].name.replace("-prompt.md", "")
    (tmp_dir / f"{prefix}-response.md").write_text(GOOD_RESPONSE, encoding="utf-8")
    ok = runner.invoke(compile_cmd, ["--root", str(tmp_path), "--check-responses"])
    assert ok.exit_code == 0, ok.output
    assert "OK" in ok.output


def test_compile_apply_partial_success(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    inbox = tmp_path / "00-Inbox"
    (inbox / "a.md").write_text("短文 A 内容。" * 20, encoding="utf-8")
    (inbox / "b.md").write_text("短文 B 内容。" * 20, encoding="utf-8")
    gen = runner.invoke(
        compile_cmd,
        ["--root", str(tmp_path), "--wave-prompts", "2", "--wave-docs", "2", "--max-chars", "8000"],
    )
    assert gen.exit_code == 0, gen.output
    tmp_dir = tmp_path / ".nexogenesis" / "tmp" / "compile"
    prompts = sorted(tmp_dir.glob("batch-*-prompt.md"))
    assert len(prompts) >= 1
    # 人为写两个 response：一个好一个坏（若只有一个 prompt，再造第二个坏文件不影响）
    p0 = prompts[0].name.replace("-prompt.md", "")
    (tmp_dir / f"{p0}-response.md").write_text(GOOD_RESPONSE, encoding="utf-8")
    (tmp_dir / "batch-099-scrap-response.md").write_text(BAD_RESPONSE, encoding="utf-8")

    result = runner.invoke(compile_cmd, ["--root", str(tmp_path), "--apply"])
    # 部分成功：应有 Buffer 落盘
    buffers = list((tmp_path / "05-Buffer").rglob("*.md"))
    assert len(buffers) >= 1, result.output
    assert (tmp_dir / "batch-099-scrap-response.md").exists()
    assert "failed_files=" in result.output or "部分 response 失败" in result.output


def test_compile_apply_single_response(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    (tmp_path / "00-Inbox" / "note.md").write_text("## 观点\n\n一条短笔记。", encoding="utf-8")
    gen = runner.invoke(compile_cmd, ["--root", str(tmp_path)])
    assert gen.exit_code == 0, gen.output
    tmp_dir = tmp_path / ".nexogenesis" / "tmp" / "compile"
    prompts = list(tmp_dir.glob("batch-*-prompt.md"))
    prefix = prompts[0].name.replace("-prompt.md", "")
    resp = tmp_dir / f"{prefix}-response.md"
    resp.write_text(GOOD_RESPONSE, encoding="utf-8")
    result = runner.invoke(
        compile_cmd,
        ["--root", str(tmp_path), "--apply", "--response", resp.name],
    )
    assert result.exit_code == 0, result.output
    assert list((tmp_path / "05-Buffer").rglob("*.md"))
