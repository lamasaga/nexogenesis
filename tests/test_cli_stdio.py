import io
import sys

from click.testing import CliRunner

from nexogenesis.cli import ensure_utf8_stdio, main
from nexogenesis.commands.digest import digest_cmd
from nexogenesis.commands.init import init_cmd


def test_ensure_utf8_stdio_reconfigures_gbk(monkeypatch):
    buf = io.BytesIO()
    stream = io.TextIOWrapper(buf, encoding="gbk", errors="strict", write_through=True)
    monkeypatch.setattr(sys, "stdout", stream)
    monkeypatch.setattr(sys, "stderr", stream)
    ensure_utf8_stdio()
    assert (sys.stdout.encoding or "").lower().replace("-", "") == "utf8"
    sys.stdout.write("路径-\U0001f4dd-笔记.md\n")
    sys.stdout.flush()


def test_digest_plan_echo_chinese_path_under_gbk_stdout(tmp_path, monkeypatch):
    """回归：经 ensure_utf8_stdio 后，digest --plan 可 echo 中文路径。"""
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    buf_dir = tmp_path / "05-Buffer" / "meaning-unit"
    buf_dir.mkdir(parents=True, exist_ok=True)
    name = "2026-07-29-认知笔记.md"
    (buf_dir / name).write_text(
        "---\ntitle: 认知\nrole: meaning-unit\nsource: s\n"
        "created: '2026-07-29'\nupdated: '2026-07-29'\nstatus: scratch\n---\n\n"
        "　　正文。\n",
        encoding="utf-8",
    )

    fake = io.TextIOWrapper(io.BytesIO(), encoding="gbk", errors="strict")
    monkeypatch.setattr(sys, "stdout", fake)
    monkeypatch.setattr(sys, "stderr", fake)
    ensure_utf8_stdio()

    result = runner.invoke(digest_cmd, ["--root", str(tmp_path), "--plan"])
    assert result.exit_code == 0, result.output
    assert "认知笔记" in result.output


def test_main_group_invokes_stdio_fix(monkeypatch):
    called = {"n": 0}

    def _spy():
        called["n"] += 1

    monkeypatch.setattr("nexogenesis.cli.ensure_utf8_stdio", _spy)
    runner = CliRunner()
    # 子命令会触发 group callback；纯 --help 不一定会
    result = runner.invoke(main, ["validate", "--help"])
    assert result.exit_code == 0
    assert called["n"] >= 1
