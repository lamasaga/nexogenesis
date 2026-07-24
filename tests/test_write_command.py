from pathlib import Path

from click.testing import CliRunner
import yaml

from nexogenesis.commands.init import init_cmd
from nexogenesis.commands.write import write_cmd


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
                "body": "教学领域核心问题。",
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
                "body": "正文内容",
            },
        ]
    }), encoding="utf-8")
    result = runner.invoke(write_cmd, ["--batch", str(batch), "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "01-Cards" / "test-claim.md").exists()
    assert (tmp_path / "01-Cards" / "_meta" / "domain-index.md").exists()
