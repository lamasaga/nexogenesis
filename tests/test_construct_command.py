from pathlib import Path

from click.testing import CliRunner

from nexogenesis.commands.construct import construct_cmd
from nexogenesis.commands.init import init_cmd


def test_construct_diagnose_default(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cards_dir = tmp_path / "01-Cards"
    (cards_dir / "teaching.md").write_text(
        "---\nid: teaching\ntitle: 教学\ntype: domain\nmaturity: growing\nlifecycle: active\n"
        "domains: [teaching]\norigin: user\nsources: []\nrelations: []\n"
        "created: '2026-07-24'\nupdated: '2026-07-24'\n---\n\n"
        "## 核心问题\n\n　　如何教学。\n\n## 边界\n\n　　原文未提及：测试。\n\n"
        "## 内在张力\n\n　　原文未提及：测试。\n\n## 原文摘录\n\n> 教学\n",
        encoding="utf-8",
    )
    buf = tmp_path / "05-Buffer" / "tension"
    buf.mkdir(parents=True, exist_ok=True)
    (buf / "2026-07-24-t.md").write_text(
        "---\ntitle: 张力\nrole: tension\nsource: s\ncreated: '2026-07-24'\n"
        "updated: '2026-07-24'\nstatus: digested\n---\n\n对立双方。\n",
        encoding="utf-8",
    )
    result = runner.invoke(construct_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    report = (tmp_path / ".nexogenesis" / "tmp" / "construct" / "lenses-report.md").read_text(
        encoding="utf-8"
    )
    assert "镜头 `distinguish`" in report
    assert "tension Buffer" in report or "未升格" in report
    # 诊断报告不应包含张力正文全文灌入标记路径以外的大段——至少不应等于把 Buffer 全文当唯一内容
    diag = (tmp_path / ".nexogenesis" / "tmp" / "construct" / "diagnose-prompt.md").read_text(
        encoding="utf-8"
    )
    assert "Buffer 索引" in diag
    assert "对立双方" not in diag  # 无全文


def test_construct_lens_prompt(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cards_dir = tmp_path / "01-Cards"
    (cards_dir / "teaching.md").write_text(
        "---\nid: teaching\ntitle: 教学\ntype: domain\nmaturity: growing\nlifecycle: active\n"
        "domains: [teaching]\norigin: user\nsources: []\nrelations: []\n"
        "created: '2026-07-24'\nupdated: '2026-07-24'\n---\n\n"
        "## 核心问题\n\n　　如何教学。\n\n## 边界\n\n　　原文未提及：测试。\n\n"
        "## 内在张力\n\n　　原文未提及：测试。\n\n## 原文摘录\n\n> 教学\n",
        encoding="utf-8",
    )
    result = runner.invoke(construct_cmd, ["--root", str(tmp_path), "--lens", "cluster"])
    assert result.exit_code == 0, result.output
    prompt = (tmp_path / ".nexogenesis" / "tmp" / "construct" / "prompt.md").read_text(
        encoding="utf-8"
    )
    assert "当前镜头：【cluster】" in prompt
    assert "teaching" in prompt


def test_construct_auto_suggests_lenses(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cards_dir = tmp_path / "01-Cards"
    (cards_dir / "teaching.md").write_text(
        "---\nid: teaching\ntitle: 教学\ntype: domain\nmaturity: growing\nlifecycle: active\n"
        "domains: [teaching]\norigin: user\nsources: []\nrelations: []\n"
        "created: '2026-07-24'\nupdated: '2026-07-24'\n---\n\n"
        "## 核心问题\n\n　　如何教学。\n\n## 边界\n\n　　原文未提及：测试。\n\n"
        "## 内在张力\n\n　　原文未提及：测试。\n\n## 原文摘录\n\n> 教学\n",
        encoding="utf-8",
    )
    buf = tmp_path / "05-Buffer" / "tension"
    buf.mkdir(parents=True, exist_ok=True)
    (buf / "2026-07-24-t.md").write_text(
        "---\ntitle: 张力\nrole: tension\nsource: s\ncreated: '2026-07-24'\n"
        "updated: '2026-07-24'\nstatus: digested\n---\n\n对立双方。\n",
        encoding="utf-8",
    )
    result = runner.invoke(construct_cmd, ["--root", str(tmp_path), "--auto"])
    assert result.exit_code == 0, result.output
    assert "AUTO" in result.output
    sug = (tmp_path / ".nexogenesis" / "tmp" / "construct" / "suggested-lenses.txt").read_text(
        encoding="utf-8"
    )
    assert "distinguish" in sug
    assert (tmp_path / ".nexogenesis" / "tmp" / "construct" / "auto-runbook.md").exists()


def test_construct_auto_applies_with_lens(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cards_dir = tmp_path / "01-Cards"
    (cards_dir / "teaching.md").write_text(
        "---\nid: teaching\ntitle: 教学\ntype: domain\nmaturity: growing\nlifecycle: active\n"
        "domains: [teaching]\norigin: user\nsources: []\nrelations: []\n"
        "created: '2026-07-24'\nupdated: '2026-07-24'\n---\n\n"
        "## 核心问题\n\n　　如何教学。\n\n## 边界\n\n　　原文未提及：测试。\n\n"
        "## 内在张力\n\n　　原文未提及：测试。\n\n## 原文摘录\n\n> 教学\n",
        encoding="utf-8",
    )
    (cards_dir / "feedback-gap-actionable.md").write_text(
        "---\nid: feedback-gap-actionable\ntitle: 教学反馈应优先指出可操作差距\ntype: claim\n"
        "maturity: growing\nlifecycle: active\ndomains: [teaching]\norigin: user\n"
        "sources: []\nrelations: []\ncreated: '2026-07-24'\nupdated: '2026-07-24'\n---\n\n"
        "## 一句话主张\n\n　　教学反馈应优先指出可操作差距。\n\n"
        "## 依据\n\n　　原文未提及：测试。\n\n## 已知限制\n\n　　原文未提及：测试。\n\n"
        "## 原文摘录\n\n> 教学反馈\n",
        encoding="utf-8",
    )

    batch = """operation:
  id: construct-auto-001
  source: 01-Cards
writes:
  - target: card
    id: feedback-gap-actionable
    type: claim
    title: 教学反馈应优先指出可操作差距
    maturity: growing
    lifecycle: active
    domains: [teaching]
    origin: user
    sources: []
    relations:
      - target: teaching
        type: applies-to
        note: 属于教学领域
    body: |
      ## 一句话主张

      　　教学反馈应优先指出可操作差距。

      ## 依据

      　　原文未提及：测试。

      ## 已知限制

      　　原文未提及：测试。

      ## 原文摘录

      > 教学反馈
    created: '2026-07-24'
    updated: '2026-07-24'
"""
    tmp_dir = tmp_path / ".nexogenesis" / "tmp" / "construct"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    (tmp_dir / "batch.yaml").write_text(batch, encoding="utf-8")

    result = runner.invoke(
        construct_cmd, ["--root", str(tmp_path), "--auto", "--lens", "cluster"]
    )
    assert result.exit_code == 0, result.output
    text = (cards_dir / "feedback-gap-actionable.md").read_text(encoding="utf-8")
    assert "applies-to" in text
    stamped = (tmp_dir / "batch.yaml").read_text(encoding="utf-8")
    assert "approved_by: agent" in stamped


def test_construct_apply_updates_card(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cards_dir = tmp_path / "01-Cards"
    (cards_dir / "teaching.md").write_text(
        "---\nid: teaching\ntitle: 教学\ntype: domain\nmaturity: growing\nlifecycle: active\n"
        "domains: [teaching]\norigin: user\nsources: []\nrelations: []\n"
        "created: '2026-07-24'\nupdated: '2026-07-24'\n---\n\n"
        "## 核心问题\n\n　　如何教学。\n\n## 边界\n\n　　原文未提及：测试。\n\n"
        "## 内在张力\n\n　　原文未提及：测试。\n\n## 原文摘录\n\n> 教学\n",
        encoding="utf-8",
    )
    (cards_dir / "feedback-gap-actionable.md").write_text(
        "---\nid: feedback-gap-actionable\ntitle: 教学反馈应优先指出可操作差距\ntype: claim\n"
        "maturity: growing\nlifecycle: active\ndomains: [teaching]\norigin: user\n"
        "sources: []\nrelations: []\ncreated: '2026-07-24'\nupdated: '2026-07-24'\n---\n\n"
        "## 一句话主张\n\n　　教学反馈应优先指出可操作差距。\n\n"
        "## 依据\n\n　　原文未提及：测试。\n\n## 已知限制\n\n　　原文未提及：测试。\n\n"
        "## 原文摘录\n\n> 教学反馈\n",
        encoding="utf-8",
    )

    batch = """operation:
  id: construct-001
  source: 01-Cards
  approved_by: user
writes:
  - target: card
    id: feedback-gap-actionable
    type: claim
    title: 教学反馈应优先指出可操作差距
    maturity: growing
    lifecycle: active
    domains: [teaching]
    origin: user
    sources: []
    relations:
      - target: teaching
        type: applies-to
        note: 属于教学领域
    body: |
      ## 一句话主张

      　　教学反馈应优先指出可操作差距。

      ## 依据

      　　原文未提及：测试。

      ## 已知限制

      　　原文未提及：测试。

      ## 原文摘录

      > 教学反馈
    created: '2026-07-24'
    updated: '2026-07-24'
"""
    tmp_dir = tmp_path / ".nexogenesis" / "tmp" / "construct"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    (tmp_dir / "batch.yaml").write_text(batch, encoding="utf-8")

    result = runner.invoke(construct_cmd, ["--root", str(tmp_path), "--apply"])
    assert result.exit_code == 0, result.output
    text = (cards_dir / "feedback-gap-actionable.md").read_text(encoding="utf-8")
    assert "applies-to" in text
