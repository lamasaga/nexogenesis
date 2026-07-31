from pathlib import Path

from click.testing import CliRunner

from nexogenesis.commands.init import init_cmd


def test_init_creates_directories(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(init_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / ".agent" / "reference" / "card-contracts" / "ontology.md").exists()
    assert (tmp_path / ".agent" / "reference" / "card-contracts" / "body-structure.md").exists()
    assert (tmp_path / ".agent" / "reference" / "card-contracts" / "card-exemplars" / "README.md").exists()
    assert (tmp_path / "05-Buffer" / "meaning-unit").exists()
    assert (tmp_path / "05-Buffer" / "tension").exists()
    assert (tmp_path / "06-Journal").exists()
