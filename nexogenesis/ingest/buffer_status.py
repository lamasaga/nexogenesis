"""解析 batch 中声明的已消费 Buffer 路径。"""

from __future__ import annotations

from pathlib import Path

import yaml

from nexogenesis.operations import BatchOperation
from nexogenesis.yaml_utils import split_frontmatter


def load_buffer_paths_by_status(buffer_dir: Path, status: str) -> list[Path]:
    paths: list[Path] = []
    if not buffer_dir.exists():
        return paths
    for subdir in buffer_dir.iterdir():
        if not subdir.is_dir() or subdir.name.startswith("_"):
            continue
        for p in subdir.glob("*.md"):
            meta, _ = split_frontmatter(p.read_text(encoding="utf-8"))
            if meta.get("status") == status:
                paths.append(p)
    return sorted(paths)


def resolve_consumed_buffers(
    root: Path,
    batch: BatchOperation | Path,
    candidates: list[Path],
    *,
    include_source_hints: bool = True,
) -> list[Path]:
    """根据 operation.consumed_buffers 与 writes.sources 匹配候选 Buffer。

    include_source_hints=False 时只认显式声明（consumed_buffers / consumed_from /
    buffer_path）：结构重挂类 batch 保留的 sources 是归因而非消费，
    不应把大批 Buffer 标成 constructed。
    """
    if isinstance(batch, Path):
        batch_op = BatchOperation.from_file(batch)
        raw = yaml.safe_load(batch.read_text(encoding="utf-8")) or {}
    else:
        batch_op = batch
        raw = {}

    hints: list[str] = list(batch_op.consumed_buffers)
    for w in batch_op.writes:
        if include_source_hints:
            for src in w.get("sources") or []:
                if isinstance(src, str):
                    hints.append(src)
        for key in ("consumed_from", "buffer_path"):
            val = w.get(key)
            if isinstance(val, str):
                hints.append(val)
            elif isinstance(val, list):
                hints.extend(str(x) for x in val)

    # 兼容未解析进 BatchOperation 的顶层字段
    op = raw.get("operation") if isinstance(raw, dict) else None
    if isinstance(op, dict):
        for x in op.get("consumed_buffers") or []:
            hints.append(str(x))

    if not hints:
        return []

    matched: list[Path] = []
    for cand in candidates:
        try:
            rel = cand.relative_to(root).as_posix()
        except ValueError:
            rel = cand.as_posix()
        name = cand.name
        for hint in hints:
            h = hint.replace("\\", "/")
            if h == rel or h.endswith("/" + name) or h == name or name in h:
                matched.append(cand)
                break
    return matched


def set_buffer_status(path: Path, old: str, new: str) -> bool:
    text = path.read_text(encoding="utf-8")
    meta, body = split_frontmatter(text)
    if meta.get("status") != old:
        return False
    meta["status"] = new
    import yaml
    from nexogenesis.yaml_utils import merge_frontmatter, atomic_write_file

    atomic_write_file(path, merge_frontmatter(meta, body))
    return True
