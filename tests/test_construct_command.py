from pathlib import Path

from click.testing import CliRunner

from nexogenesis.commands.construct import construct_cmd
from nexogenesis.commands.init import init_cmd


def test_construct_generates_prompt(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cards_dir = tmp_path / "01-Cards"
    (cards_dir / "teaching.md").write_text(
        "---\nid: teaching\ntitle: 教学\ntype: domain\nmaturity: growing\nlifecycle: active\ndomains: [teaching]\norigin: user\nsources: []\nrelations: []\ncreated: '2026-07-24'\nupdated: '2026-07-24'\n---\n", encoding="utf-8"
    )
    result = runner.invoke(construct_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".nexogenesis" / "tmp" / "construct" / "prompt.md").exists()


def test_construct_apply_updates_card(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cards_dir = tmp_path / "01-Cards"
    (cards_dir / "teaching.md").write_text(
        "---\nid: teaching\ntitle: 教学\ntype: domain\nmaturity: growing\nlifecycle: active\ndomains: [teaching]\norigin: user\nsources: []\nrelations: []\ncreated: '2026-07-24'\nupdated: '2026-07-24'\n---\n", encoding="utf-8"
    )
    (cards_dir / "feedback-gap-actionable.md").write_text(
        "---\nid: feedback-gap-actionable\ntitle: 教学反馈应优先指出可操作差距\ntype: claim\nmaturity: growing\nlifecycle: active\ndomains: [teaching]\norigin: user\nsources: []\nrelations: []\ncreated: '2026-07-24'\nupdated: '2026-07-24'\n---\n", encoding="utf-8"
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
    body: 教学反馈应优先指出可操作差距。
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
