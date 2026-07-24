from pathlib import Path

from click.testing import CliRunner

from nexogenesis.commands.index import index_cmd
from nexogenesis.commands.init import init_cmd


def test_index_generates_files(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    result = runner.invoke(index_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "01-Cards" / "_meta" / "domain-index.md").exists()
