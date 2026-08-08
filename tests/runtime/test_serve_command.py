from click.testing import CliRunner

from nexogenesis.cli import main


def test_serve_help():
    result = CliRunner().invoke(main, ["serve", "--help"])
    assert result.exit_code == 0
    assert "--port" in result.output
    assert "--root" in result.output
