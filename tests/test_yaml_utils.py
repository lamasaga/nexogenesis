from pathlib import Path

from nexogenesis.yaml_utils import (
    atomic_write_file,
    dump_yaml,
    load_yaml,
    merge_frontmatter,
    split_frontmatter,
)


def test_round_trip_yaml(tmp_path: Path):
    path = tmp_path / "test.yaml"
    dump_yaml({"a": 1}, path)
    assert load_yaml(path) == {"a": 1}


def test_atomic_write(tmp_path: Path):
    path = tmp_path / "out.txt"
    atomic_write_file(path, "hello")
    assert path.read_text(encoding="utf-8") == "hello"


def test_split_merge_frontmatter():
    text = "---\ntitle: T\n---\n\nbody"
    meta, body = split_frontmatter(text)
    assert meta == {"title": "T"}
    assert body == "body"
    restored = merge_frontmatter(meta, body)
    assert "---" in restored
