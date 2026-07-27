from pathlib import Path

from click.testing import CliRunner

from nexogenesis.commands.digest import digest_cmd
from nexogenesis.commands.init import init_cmd


def _write_scratch(buf_dir: Path, name: str, title: str) -> None:
    buf_dir.joinpath(name).write_text(
        "---\n"
        f"title: {title}\n"
        "role: meaning-unit\n"
        "source: s\n"
        "created: '2026-07-24'\n"
        "updated: '2026-07-24'\n"
        "status: scratch\n"
        "---\n\n"
        "### 核心表达\n\n　　内容。\n\n"
        "### 依据与细节\n\n　　原文未提及：测试。\n\n"
        "### 限制与边界\n\n　　原文未提及：测试。\n\n"
        "### 原文摘录\n\n> x\n",
        encoding="utf-8",
    )


def test_digest_generates_prompt(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    buf_dir = tmp_path / "05-Buffer" / "meaning-unit"
    buf_dir.mkdir(parents=True, exist_ok=True)
    _write_scratch(buf_dir, "2026-07-24-test.md", "t")
    result = runner.invoke(digest_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    prompt = (tmp_path / ".nexogenesis" / "tmp" / "digest" / "prompt.md").read_text(encoding="utf-8")
    assert "空库" in prompt or "bootstrap" in prompt.lower() or "必须先" in prompt
    assert "卡片目录" in prompt


def test_digest_wave_limits_buffers(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    buf_dir = tmp_path / "05-Buffer" / "meaning-unit"
    buf_dir.mkdir(parents=True, exist_ok=True)
    for i in range(12):
        _write_scratch(buf_dir, f"2026-07-24-{i:02d}.md", f"t{i}")
    plan = runner.invoke(digest_cmd, ["--root", str(tmp_path), "--plan", "--wave-buffers", "3"])
    assert plan.exit_code == 0, plan.output
    assert "selected=3" in plan.output
    assert "deferred=9" in plan.output
    result = runner.invoke(digest_cmd, ["--root", str(tmp_path), "--wave-buffers", "3"])
    assert result.exit_code == 0, result.output
    prompt = (tmp_path / ".nexogenesis" / "tmp" / "digest" / "prompt.md").read_text(encoding="utf-8")
    # 全文区不应出现全部 12 个路径
    assert prompt.count("05-Buffer/meaning-unit/") <= 6


def test_digest_auto_generates_runbook(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    buf_dir = tmp_path / "05-Buffer" / "meaning-unit"
    buf_dir.mkdir(parents=True, exist_ok=True)
    _write_scratch(buf_dir, "2026-07-24-test.md", "t")
    result = runner.invoke(digest_cmd, ["--root", str(tmp_path), "--auto"])
    assert result.exit_code == 0, result.output
    assert "AUTO" in result.output
    assert (tmp_path / ".nexogenesis" / "tmp" / "digest" / "auto-runbook.md").exists()
    assert (tmp_path / ".nexogenesis" / "tmp" / "digest" / "prompt.md").exists()


def test_digest_auto_applies_after_batch(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])

    cards_dir = tmp_path / "01-Cards"
    (cards_dir / "教学.md").write_text(
        "---\nid: 教学\ntitle: 教学\ntype: domain\nmaturity: growing\nlifecycle: active\n"
        "domains: [教学]\norigin: user\nsources: []\nrelations: []\n"
        "created: '2026-07-24'\nupdated: '2026-07-24'\n---\n\n"
        "## 核心问题\n\n　　如何有效教学。\n\n## 边界\n\n　　原文未提及：测试。\n\n"
        "## 内在张力\n\n　　原文未提及：测试。\n\n## 原文摘录\n\n> 测试\n",
        encoding="utf-8",
    )

    buf_dir = tmp_path / "05-Buffer" / "meaning-unit"
    buf_dir.mkdir(parents=True, exist_ok=True)
    (buf_dir / "2026-07-24-test.md").write_text(
        "---\ntitle: 教学反馈\nrole: meaning-unit\nsource: s\n"
        "created: '2026-07-24'\nupdated: '2026-07-24'\nstatus: scratch\n---\n\n"
        "## 核心表达\n\n　　教学反馈应优先指出可操作差距。\n\n"
        "## 依据与细节\n\n　　原文未提及：测试。\n\n"
        "## 限制与边界\n\n　　原文未提及：测试。\n\n"
        "## 原文摘录\n\n> 教学反馈应优先指出可操作差距。\n",
        encoding="utf-8",
    )

    batch = """operation:
  id: digest-auto-001
  source: 05-Buffer
  approved_by: pending
  consumed_buffers:
    - 05-Buffer/meaning-unit/2026-07-24-test.md
writes:
  - target: card
    id: 教学反馈应指出可操作差距
    type: claim
    title: 教学反馈应优先指出可操作差距
    maturity: seed
    lifecycle: active
    domains: [教学]
    origin: document
    sources: ["05-Buffer/meaning-unit/2026-07-24-test.md"]
    relations: []
    body: |
      ## 一句话主张

      　　教学反馈应优先指出可操作差距。

      ## 依据

      　　原文未提及：测试。

      ## 已知限制

      　　原文未提及：测试。

      ## 原文摘录

      > 教学反馈应优先指出可操作差距。
    created: '2026-07-24'
    updated: '2026-07-24'
"""
    tmp_dir = tmp_path / ".nexogenesis" / "tmp" / "digest"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    (tmp_dir / "batch.yaml").write_text(batch, encoding="utf-8")

    result = runner.invoke(digest_cmd, ["--root", str(tmp_path), "--auto"])
    assert result.exit_code == 0, result.output
    assert (cards_dir / "教学反馈应指出可操作差距.md").exists()
    stamped = (tmp_dir / "batch.yaml").read_text(encoding="utf-8")
    assert "approved_by: agent" in stamped
    buf_text = (buf_dir / "2026-07-24-test.md").read_text(encoding="utf-8")
    assert "status: digested" in buf_text


def test_digest_auto_rejects_bad_batch(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    buf_dir = tmp_path / "05-Buffer" / "meaning-unit"
    buf_dir.mkdir(parents=True, exist_ok=True)
    _write_scratch(buf_dir, "2026-07-24-test.md", "t")
    tmp_dir = tmp_path / ".nexogenesis" / "tmp" / "digest"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    (tmp_dir / "batch.yaml").write_text(
        "operation:\n  id: x\n  source: s\nwrites: []\n",
        encoding="utf-8",
    )
    result = runner.invoke(digest_cmd, ["--root", str(tmp_path), "--auto"])
    assert result.exit_code != 0
    assert "自检失败" in result.output


def test_digest_apply_writes_card(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])

    cards_dir = tmp_path / "01-Cards"
    (cards_dir / "教学.md").write_text(
        "---\nid: 教学\ntitle: 教学\ntype: domain\nmaturity: growing\nlifecycle: active\n"
        "domains: [教学]\norigin: user\nsources: []\nrelations: []\n"
        "created: '2026-07-24'\nupdated: '2026-07-24'\n---\n\n"
        "## 核心问题\n\n　　如何有效教学。\n\n## 边界\n\n　　原文未提及：测试。\n\n"
        "## 内在张力\n\n　　原文未提及：测试。\n\n## 原文摘录\n\n> 测试\n",
        encoding="utf-8",
    )

    buf_dir = tmp_path / "05-Buffer" / "meaning-unit"
    buf_dir.mkdir(parents=True, exist_ok=True)
    (buf_dir / "2026-07-24-test.md").write_text(
        "---\ntitle: 教学反馈\nrole: meaning-unit\nsource: s\n"
        "created: '2026-07-24'\nupdated: '2026-07-24'\nstatus: scratch\n---\n\n"
        "## 核心表达\n\n　　教学反馈应优先指出可操作差距。\n\n"
        "## 依据与细节\n\n　　原文未提及：测试。\n\n"
        "## 限制与边界\n\n　　原文未提及：测试。\n\n"
        "## 原文摘录\n\n> 教学反馈应优先指出可操作差距。\n",
        encoding="utf-8",
    )

    batch = """operation:
  id: digest-001
  source: 05-Buffer
  approved_by: user
  consumed_buffers:
    - 05-Buffer/meaning-unit/2026-07-24-test.md
writes:
  - target: card
    id: 教学反馈应指出可操作差距
    type: claim
    title: 教学反馈应优先指出可操作差距
    maturity: seed
    lifecycle: active
    domains: [教学]
    origin: document
    sources: ["05-Buffer/meaning-unit/2026-07-24-test.md"]
    relations: []
    body: |
      ## 一句话主张

      　　教学反馈应优先指出可操作差距。

      ## 依据

      　　原文未提及：测试。

      ## 已知限制

      　　原文未提及：测试。

      ## 原文摘录

      > 教学反馈应优先指出可操作差距。
    created: '2026-07-24'
    updated: '2026-07-24'
"""
    tmp_dir = tmp_path / ".nexogenesis" / "tmp" / "digest"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    (tmp_dir / "batch.yaml").write_text(batch, encoding="utf-8")

    result = runner.invoke(digest_cmd, ["--root", str(tmp_path), "--apply"])
    assert result.exit_code == 0, result.output
    assert (cards_dir / "教学反馈应指出可操作差距.md").exists()
    buf_text = (buf_dir / "2026-07-24-test.md").read_text(encoding="utf-8")
    assert "status: digested" in buf_text
