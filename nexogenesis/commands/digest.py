from pathlib import Path

import click

from nexogenesis import journal
from nexogenesis.commands.write import write_cmd
from nexogenesis.ingest.prompts import render_digest_prompt
from nexogenesis.store import Store
from nexogenesis.yaml_utils import atomic_write_file


def _load_buffer_paths(buffer_dir: Path, status: str) -> list[Path]:
    paths = []
    for subdir in buffer_dir.iterdir():
        if not subdir.is_dir() or subdir.name.startswith("_"):
            continue
        for p in subdir.glob("*.md"):
            text = p.read_text(encoding="utf-8")
            if f"status: {status}" in text:
                paths.append(p)
    return sorted(paths)


def _parse_questions(profile_path: Path) -> list[str]:
    questions = []
    if not profile_path.exists():
        return questions
    for line in profile_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("|") and "问题" not in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3 and parts[1]:
                questions.append(parts[1])
    return questions


def _load_buffers(buffer_paths: list[Path]) -> list[dict]:
    return [{"path": str(p), "text": p.read_text(encoding="utf-8")} for p in buffer_paths]


def _load_cards(cards_dir: Path) -> list[dict]:
    store = Store(cards_dir).load()
    return [
        {
            "id": c.id,
            "title": c.title,
            "type": c.type.value,
            "domains": c.domains,
            "relations": [{"target": r.target, "type": r.type.value, "note": r.note} for r in c.relations],
        }
        for c in store.cards.values()
    ]


@click.command()
@click.option("--root", default=".", help="项目根目录")
@click.option("--status", default="scratch", help="要消化的 Buffer 状态")
@click.option("--apply", is_flag=True, help="应用 batch 文件写入卡片")
def digest_cmd(root, status, apply):
    root_path = Path(root).resolve()
    buffer_dir = root_path / "05-Buffer"
    cards_dir = root_path / "01-Cards"
    profile_path = root_path / "02-Profile" / "问题清单.md"
    tmp_dir = root_path / ".nexogenesis" / "tmp" / "digest"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    buffer_paths = _load_buffer_paths(buffer_dir, status)
    if not buffer_paths:
        click.echo("没有待消化的 Buffer。")
        return

    cards = _load_cards(cards_dir)
    questions = _parse_questions(profile_path)
    buffers = _load_buffers(buffer_paths)

    prompt = render_digest_prompt(buffers, cards, questions)
    prompt_path = tmp_dir / "prompt.md"
    atomic_write_file(prompt_path, prompt)

    batch_path = tmp_dir / "batch.yaml"

    if not apply:
        click.echo(f"已生成 digest prompt: {prompt_path}")
        click.echo(f"请 Agent 调用 LLM 并将 batch YAML 保存到 {batch_path}，确认后运行 --apply。")
        return

    if not batch_path.exists():
        raise click.ClickException(f"未找到 {batch_path}，请先生成并确认 batch。")

    ctx = click.Context(write_cmd)
    ctx.invoke(write_cmd, batch=str(batch_path), root=str(root_path))

    for p in buffer_paths:
        text = p.read_text(encoding="utf-8")
        text = text.replace(f"status: {status}", "status: digested")
        atomic_write_file(p, text)

    journal.append(
        root_path,
        f"digest-{len(buffer_paths)}",
        "digest",
        [str(p.relative_to(root_path)) for p in buffer_paths],
        "05-Buffer",
        "user",
    )
    click.echo(f"Digest applied: {len(buffer_paths)} buffers consumed.")
