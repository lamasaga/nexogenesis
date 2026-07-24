from pathlib import Path

from click.testing import CliRunner

from nexogenesis.commands.init import init_cmd
from nexogenesis.commands.validate import validate_cmd


def test_validate_passes_after_init(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    result = runner.invoke(validate_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0
