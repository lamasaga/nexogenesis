from pathlib import Path

from click.testing import CliRunner

from nexogenesis.commands.digest import digest_cmd
from nexogenesis.commands.init import init_cmd


def test_digest_generates_prompt(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    buf_dir = tmp_path / "05-Buffer" / "claim"
    buf_dir.mkdir(parents=True, exist_ok=True)
    buf_dir.joinpath("2026-07-24-test.md").write_text(
        "---\ntitle: t\ntype: claim\nstatus: scratch\n---\nbody", encoding="utf-8"
    )
    result = runner.invoke(digest_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".nexogenesis" / "tmp" / "digest" / "prompt.md").exists()


def test_digest_apply_writes_card(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])

    # Domain card
    cards_dir = tmp_path / "01-Cards"
    (cards_dir / "teaching.md").write_text(
        "---\nid: teaching\ntitle: 教学\ntype: domain\nmaturity: growing\nlifecycle: active\ndomains: [teaching]\norigin: user\nsources: []\nrelations: []\ncreated: '2026-07-24'\nupdated: '2026-07-24'\n---\n", encoding="utf-8"
    )

    # Buffer
    buf_dir = tmp_path / "05-Buffer" / "claim"
    buf_dir.mkdir(parents=True, exist_ok=True)
    (buf_dir / "2026-07-24-test.md").write_text(
        "---\ntitle: 教学反馈\ntype: claim\nstatus: scratch\n---\n教学反馈应优先指出可操作差距。", encoding="utf-8"
    )

    # Batch file
    batch = """operation:
  id: digest-001
  source: 05-Buffer
  approved_by: user
writes:
  - target: card
    id: feedback-gap-actionable
    type: claim
    title: 教学反馈应优先指出可操作差距
    maturity: seed
    lifecycle: active
    domains: [teaching]
    origin: document
    sources: ["05-Buffer/2026-07-24-test.md"]
    relations: []
    body: 教学反馈应优先指出可操作差距。
    created: '2026-07-24'
    updated: '2026-07-24'
"""
    tmp_dir = tmp_path / ".nexogenesis" / "tmp" / "digest"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    (tmp_dir / "batch.yaml").write_text(batch, encoding="utf-8")

    result = runner.invoke(digest_cmd, ["--root", str(tmp_path), "--apply"])
    assert result.exit_code == 0, result.output
    assert (cards_dir / "feedback-gap-actionable.md").exists()
    buf_text = (buf_dir / "2026-07-24-test.md").read_text(encoding="utf-8")
    assert "status: digested" in buf_text
