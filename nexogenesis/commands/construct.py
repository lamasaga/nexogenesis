from pathlib import Path

import click

from nexogenesis import journal
from nexogenesis.commands.write import write_cmd
from nexogenesis.ingest.buffer_status import (
    load_buffer_paths_by_status,
    resolve_consumed_buffers,
    set_buffer_status,
)
from nexogenesis.ingest.prompts import render_construct_prompt
from nexogenesis.operations import BatchOperation
from nexogenesis.store import Store
from nexogenesis.yaml_utils import atomic_write_file


def _load_all_buffers(buffer_dir: Path, root: Path) -> list[dict]:
    buffers = []
    if not buffer_dir.exists():
        return buffers
    for subdir in buffer_dir.iterdir():
        if not subdir.is_dir() or subdir.name.startswith("_"):
            continue
        for p in subdir.glob("*.md"):
            try:
                rel = p.relative_to(root).as_posix()
            except ValueError:
                rel = str(p)
            buffers.append({"path": rel, "text": p.read_text(encoding="utf-8")})
    return buffers


def _load_cards(cards_dir: Path) -> list[dict]:
    store = Store(cards_dir).load()
    return [
        {
            "id": c.id,
            "title": c.title,
            "type": c.type.value,
            "domains": c.domains,
            "relations": [
                {"target": r.target, "type": r.type.value, "note": r.note} for r in c.relations
            ],
            "body": c.body or "",
        }
        for c in store.cards.values()
    ]


def _parse_questions(profile_path: Path) -> list[str]:
    questions = []
    if not profile_path.exists():
        return questions
    for line in profile_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("|") and "问题" not in line and "---" not in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3 and parts[1]:
                questions.append(parts[1])
    return questions


@click.command()
@click.option("--root", default=".", help="项目根目录")
@click.option("--apply", is_flag=True, help="应用 batch 文件写入卡片")
def construct_cmd(root, apply):
    root_path = Path(root).resolve()
    buffer_dir = root_path / "05-Buffer"
    cards_dir = root_path / "01-Cards"
    profile_path = root_path / "02-Profile" / "问题清单.md"
    tmp_dir = root_path / ".nexogenesis" / "tmp" / "construct"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    cards = _load_cards(cards_dir)
    buffers = _load_all_buffers(buffer_dir, root_path)
    questions = _parse_questions(profile_path)

    prompt = render_construct_prompt(cards, buffers, questions)
    prompt_path = tmp_dir / "prompt.md"
    atomic_write_file(prompt_path, prompt)

    batch_path = tmp_dir / "batch.yaml"

    if not apply:
        click.echo(f"已生成 construct prompt: {prompt_path}")
        click.echo(
            f"请 Agent 调用 LLM 并将 batch YAML 保存到 {batch_path}；"
            "若需标记 Buffer，请在 operation.consumed_buffers 列出 digested 路径，确认后 --apply。"
        )
        return

    if not batch_path.exists():
        raise click.ClickException(f"未找到 {batch_path}，请先生成并确认 batch。")

    ctx = click.Context(write_cmd)
    ctx.invoke(write_cmd, batch=str(batch_path), root=str(root_path))

    digested = load_buffer_paths_by_status(buffer_dir, "digested")
    batch_op = BatchOperation.from_file(batch_path)
    consumed = resolve_consumed_buffers(root_path, batch_op, digested)
    marked = 0
    for p in consumed:
        if set_buffer_status(p, "digested", "constructed"):
            marked += 1

    journal.append(
        root_path,
        "construct",
        "construct",
        [c["id"] for c in cards],
        "01-Cards + 05-Buffer",
        "user",
    )
    click.echo(f"Construct applied. Marked {marked} buffer(s) constructed.")
