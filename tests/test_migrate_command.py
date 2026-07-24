from pathlib import Path

from click.testing import CliRunner

from nexogenesis.commands.init import init_cmd
from nexogenesis.commands.migrate import migrate_cmd


def test_migrate_dry_run(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    result = runner.invoke(migrate_cmd, ["--to", "default", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "dry-run" in result.output
