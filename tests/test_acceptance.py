from pathlib import Path

import yaml
from click.testing import CliRunner

from nexogenesis.commands.init import init_cmd
from nexogenesis.commands.index import index_cmd
from nexogenesis.commands.validate import validate_cmd
from nexogenesis.commands.write import write_cmd


def _batch(operation_id: str, writes: list) -> str:
    return yaml.safe_dump(
        {
            "operation": {
                "id": operation_id,
                "source": "acceptance test",
                "approved_by": "user",
            },
            "writes": writes,
        },
        allow_unicode=True,
        sort_keys=False,
    )


def test_full_capture_loop_is_idempotent(tmp_path: Path):
    runner = CliRunner()

    # init
    result = runner.invoke(init_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0, result.output

    # Prepare batch: a domain and a claim belonging to it
    batch_file = tmp_path / "batch.yaml"
    batch_file.write_text(
        _batch(
            "2026-07-24-acceptance-001",
            [
                {
                    "target": "card",
                    "id": "teaching",
                    "type": "domain",
                    "title": "教学领域",
                    "maturity": "growing",
                    "lifecycle": "active",
                    "domains": ["teaching"],
                    "origin": "user",
                    "sources": ["用户对话"],
                    "relations": [],
                    "body": (
                        "## 核心问题\n\n　　教学如何有效发生。\n\n"
                        "## 边界\n\n　　原文未提及：验收测试未展开。\n\n"
                        "## 内在张力\n\n　　原文未提及：验收测试未展开。\n\n"
                        "## 原文摘录\n\n> 教学领域\n"
                    ),
                    "created": "2026-07-24",
                    "updated": "2026-07-24",
                },
                {
                    "target": "card",
                    "id": "feedback-gap-actionable",
                    "type": "claim",
                    "title": "教学反馈应优先指出可操作差距",
                    "maturity": "growing",
                    "lifecycle": "active",
                    "domains": ["teaching"],
                    "origin": "user",
                    "sources": ["2026-07-24 用户对话"],
                    "relations": [],
                    "body": (
                        "## 一句话主张\n\n　　教学反馈应优先指出可操作差距。\n\n"
                        "## 依据\n\n　　教师在给出反馈时，应明确指出学生当前表现与目标之间的差距，并提供可操作的建议。\n\n"
                        "## 已知限制\n\n　　原文未提及：验收测试未展开。\n\n"
                        "## 原文摘录\n\n> 教师在给出反馈时，应明确指出学生当前表现与目标之间的差距\n"
                    ),
                    "created": "2026-07-24",
                    "updated": "2026-07-24",
                },
                {
                    "target": "profile_question",
                    "question": "怎样区分有效反思与自我感动？",
                    "added_at": "2026-07-24",
                },
            ],
        ),
        encoding="utf-8",
    )

    # First write
    result = runner.invoke(write_cmd, ["--batch", str(batch_file), "--root", str(tmp_path)])
    assert result.exit_code == 0, result.output

    cards_dir = tmp_path / "01-Cards"
    assert (cards_dir / "teaching.md").exists()
    assert (cards_dir / "feedback-gap-actionable.md").exists()
    assert (tmp_path / "02-Profile" / "问题清单.md").exists()

    # Validate passes
    result = runner.invoke(validate_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0, result.output

    # Indexes generated
    result = runner.invoke(index_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (cards_dir / "_meta" / "domain-index.md").exists()
    assert (cards_dir / "_meta" / "conflict-index.md").exists()
    assert (cards_dir / "_meta" / "theory-index.md").exists()

    # Journal entry recorded
    journal_files = list((tmp_path / "06-Journal").glob("*.md"))
    assert journal_files

    # Repeat the same write and ensure no duplicate cards are created
    card_files_before = set(cards_dir.glob("*.md"))
    result = runner.invoke(write_cmd, ["--batch", str(batch_file), "--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    card_files_after = set(cards_dir.glob("*.md"))
    assert card_files_before == card_files_after

    # Verify claim file still has the core claim once in 一句话主张
    claim_text = (cards_dir / "feedback-gap-actionable.md").read_text(encoding="utf-8")
    assert claim_text.count("## 一句话主张") == 1
    assert "教学反馈应优先指出可操作差距" in claim_text


def test_write_rolls_back_on_validation_failure(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])

    batch_file = tmp_path / "invalid-batch.yaml"
    # claim references a non-existent domain -> orphan
    batch_file.write_text(
        _batch(
            "2026-07-24-acceptance-002",
            [
                {
                    "target": "card",
                    "id": "orphan-claim",
                    "type": "claim",
                    "title": "Orphan Claim",
                    "maturity": "growing",
                    "lifecycle": "active",
                    "domains": ["nonexistent-domain"],
                    "origin": "system",
                    "sources": [],
                    "relations": [],
                    "body": "This should not be persisted.",
                    "created": "2026-07-24",
                    "updated": "2026-07-24",
                }
            ],
        ),
        encoding="utf-8",
    )

    result = runner.invoke(write_cmd, ["--batch", str(batch_file), "--root", str(tmp_path)])
    assert result.exit_code != 0, result.output
    assert not (tmp_path / "01-Cards" / "orphan-claim.md").exists()

    # Journal should not have been updated for the failed operation
    journal_files = list((tmp_path / "06-Journal").glob("*.md"))
    assert len(journal_files) == 0
