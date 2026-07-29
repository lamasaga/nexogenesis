from pathlib import Path

from click.testing import CliRunner

from nexogenesis.commands.compile import compile_cmd, _archive_doc
from nexogenesis.commands.init import init_cmd
from nexogenesis.ingest.ingest import scan_inbox


def test_scan_inbox(tmp_path: Path):
    (tmp_path / "a.md").write_text("text", encoding="utf-8")
    (tmp_path / "b.txt").write_text("text", encoding="utf-8")
    docs = scan_inbox(tmp_path)
    assert len(docs) == 2
    assert {d["name"] for d in docs} == {"a.md", "b.txt"}


def test_scan_inbox_recursive_default(tmp_path: Path):
    (tmp_path / "top.md").write_text("t", encoding="utf-8")
    sub = tmp_path / "01-sub"
    sub.mkdir()
    (sub / "nested.md").write_text("n", encoding="utf-8")
    docs = scan_inbox(tmp_path)
    assert len(docs) == 2
    assert {d["name"] for d in docs} == {"top.md", "01-sub/nested.md"}
    assert len(scan_inbox(tmp_path, recursive=False)) == 1


def test_scan_inbox_skips_dot_dirs(tmp_path: Path):
    hidden = tmp_path / ".cache"
    hidden.mkdir()
    (hidden / "secret.md").write_text("x", encoding="utf-8")
    (tmp_path / "ok.md").write_text("y", encoding="utf-8")
    docs = scan_inbox(tmp_path)
    assert len(docs) == 1
    assert docs[0]["name"] == "ok.md"


def test_archive_preserves_subdir(tmp_path: Path):
    inbox = tmp_path / "00-Inbox"
    archive = tmp_path / "03-Archive"
    nested = inbox / "papers"
    nested.mkdir(parents=True)
    src = nested / "a.md"
    src.write_text("hello", encoding="utf-8")
    target = _archive_doc(src, archive, inbox_dir=inbox)
    assert target == archive / "papers" / "a.md"
    assert target.exists()
    assert not src.exists()
    assert not nested.exists()  # empty parent cleaned


def test_compile_plan_sees_subdir(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    nested = tmp_path / "00-Inbox" / "batch-a"
    nested.mkdir(parents=True)
    (nested / "note.md").write_text("子目录笔记内容。" * 20, encoding="utf-8")
    (tmp_path / "00-Inbox" / "top.md").write_text("顶层笔记内容。" * 20, encoding="utf-8")
    result = runner.invoke(compile_cmd, ["--root", str(tmp_path), "--plan"])
    assert result.exit_code == 0, result.output
    assert "batch-a/note.md" in result.output
    assert "top.md" in result.output
    # --no-recursive 只见顶层
    result2 = runner.invoke(
        compile_cmd, ["--root", str(tmp_path), "--plan", "--no-recursive"]
    )
    assert result2.exit_code == 0, result2.output
    assert "top.md" in result2.output
    assert "batch-a/note.md" not in result2.output
