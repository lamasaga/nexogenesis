from pathlib import Path

from click.testing import CliRunner
import yaml

from nexogenesis.commands.init import init_cmd
from nexogenesis.commands.write import write_cmd


def _domain_body():
    return (
        "## 核心问题\n\n　　如何教学。\n\n## 边界\n\n　　原文未提及：测试。\n\n"
        "## 内在张力\n\n　　原文未提及：测试。\n\n## 原文摘录\n\n> 教学\n"
    )


def _claim_body():
    return (
        "## 一句话主张\n\n　　测试主张。\n\n## 依据\n\n　　原文未提及：测试。\n\n"
        "## 已知限制\n\n　　原文未提及：测试。\n\n## 原文摘录\n\n> 测试\n"
    )


def test_write_creates_card(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    batch = tmp_path / "batch.yaml"
    batch.write_text(yaml.safe_dump({
        "operation": {"id": "op-1", "source": "对话", "approved_by": "user"},
        "writes": [
            {
                "target": "card",
                "id": "teaching",
                "title": "教学领域",
                "type": "domain",
                "maturity": "mature",
                "lifecycle": "active",
                "domains": ["teaching"],
                "origin": "user",
                "sources": ["对话"],
                "relations": [],
                "created": "2026-07-24",
                "updated": "2026-07-24",
                "body": _domain_body(),
            },
            {
                "target": "card",
                "id": "test-claim",
                "title": "测试主张",
                "type": "claim",
                "maturity": "growing",
                "lifecycle": "active",
                "domains": ["teaching"],
                "origin": "user",
                "sources": ["对话"],
                "relations": [],
                "created": "2026-07-24",
                "updated": "2026-07-24",
                "body": _claim_body(),
            },
        ]
    }, allow_unicode=True), encoding="utf-8")
    result = runner.invoke(write_cmd, ["--batch", str(batch), "--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "01-Cards" / "test-claim.md").exists()
    assert (tmp_path / "01-Cards" / "_meta" / "domain-index.md").exists()


def test_write_preserves_created_on_update(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    batch1 = tmp_path / "b1.yaml"
    batch1.write_text(yaml.safe_dump({
        "operation": {"id": "op-c1", "source": "t", "approved_by": "user"},
        "writes": [{
            "target": "card", "id": "teaching", "title": "教学", "type": "domain",
            "maturity": "growing", "lifecycle": "active", "domains": ["teaching"],
            "origin": "user", "sources": [], "relations": [],
            "created": "2026-01-01", "updated": "2026-01-01", "body": _domain_body(),
        }],
    }, allow_unicode=True), encoding="utf-8")
    assert runner.invoke(write_cmd, ["--batch", str(batch1), "--root", str(tmp_path)]).exit_code == 0

    batch2 = tmp_path / "b2.yaml"
    batch2.write_text(yaml.safe_dump({
        "operation": {"id": "op-c2", "source": "t", "approved_by": "user"},
        "writes": [{
            "target": "card", "id": "teaching", "title": "教学", "type": "domain",
            "maturity": "growing", "lifecycle": "active", "domains": ["teaching"],
            "origin": "user", "sources": [], "relations": [],
            "created": "2026-12-31", "updated": "2026-07-27", "body": _domain_body(),
        }],
    }, allow_unicode=True), encoding="utf-8")
    assert runner.invoke(write_cmd, ["--batch", str(batch2), "--root", str(tmp_path)]).exit_code == 0
    text = (tmp_path / "01-Cards" / "teaching.md").read_text(encoding="utf-8")
    assert "2026-01-01" in text


def test_write_rejects_ghost_link_and_keeps_profile_clean(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    batch = tmp_path / "bad.yaml"
    batch.write_text(yaml.safe_dump({
        "operation": {"id": "op-bad", "source": "t", "approved_by": "user"},
        "writes": [
            {
                "target": "card", "id": "teaching", "title": "教学", "type": "domain",
                "maturity": "growing", "lifecycle": "active", "domains": ["teaching"],
                "origin": "user", "sources": [], "relations": [],
                "created": "2026-07-24", "updated": "2026-07-24",
                "body": _domain_body() + "\n参见 [[不存在的卡]]\n",
            },
            {
                "target": "profile_question",
                "question": "不该写入的问题",
                "added_at": "2026-07-24",
            },
        ],
    }, allow_unicode=True), encoding="utf-8")
    result = runner.invoke(write_cmd, ["--batch", str(batch), "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert not (tmp_path / "01-Cards" / "teaching.md").exists()
    profile = tmp_path / "02-Profile" / "问题清单.md"
    if profile.exists():
        assert "不该写入的问题" not in profile.read_text(encoding="utf-8")


def test_write_rejects_system_mature_without_promotion_flag(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    batch = tmp_path / "sys.yaml"
    batch.write_text(yaml.safe_dump({
        "operation": {"id": "op-sys", "source": "t", "approved_by": "user"},
        "writes": [{
            "target": "card", "id": "teaching", "title": "教学", "type": "domain",
            "maturity": "mature", "lifecycle": "active", "domains": ["teaching"],
            "origin": "system", "sources": [], "relations": [],
            "created": "2026-07-24", "updated": "2026-07-24", "body": _domain_body(),
        }],
    }, allow_unicode=True), encoding="utf-8")
    result = runner.invoke(write_cmd, ["--batch", str(batch), "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert not (tmp_path / "01-Cards" / "teaching.md").exists()
