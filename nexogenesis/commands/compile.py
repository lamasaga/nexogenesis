import shutil
from pathlib import Path

import click
import yaml

from nexogenesis import journal
from nexogenesis.commands.index import generate_indexes
from nexogenesis.commands.validate import run_validate
from nexogenesis.ingest import ensure_buffer_dirs
from nexogenesis.ingest.batch_runner import build_batches, format_batch_prompt, parse_llm_buffers, write_buffer
from nexogenesis.ingest.chunker import build_compile_units
from nexogenesis.ingest.ingest import build_compile_plan, scan_inbox
from nexogenesis.yaml_utils import atomic_write_file


DEEP_MODE_DOC_GUARD = 5


def _parse_genres_arg(arg: str) -> dict:
    genres = {}
    if not arg:
        return genres
    for pair in arg.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if "=" not in pair:
            raise click.ClickException(f"--genres 格式错误：{pair!r}")
        name, genre = pair.split("=", 1)
        genres[name.strip()] = genre.strip()
    return genres


def _write_prompts(batches: list, deep: bool, tmp_dir: Path) -> list[Path]:
    paths = []
    for idx, batch in enumerate(batches, 1):
        genre = batch[0].get("genre") or "generic"
        prompt = format_batch_prompt(batch, genre=genre, deep=deep)
        p = tmp_dir / f"batch-{idx:03d}-{genre}-prompt.md"
        atomic_write_file(p, prompt)
        paths.append(p)
    return paths


def _apply_responses(tmp_dir: Path, buffer_dir: Path, default_source: str) -> list[Path]:
    response_files = sorted(tmp_dir.glob("batch-*-response.*"))
    if not response_files:
        raise click.ClickException(
            "未找到 LLM response 文件。请先让 Agent 调用 LLM，"
            "并将每个 response 保存为 .nexogenesis/tmp/compile/batch-XXX-response.md 或 .yaml"
        )
    written = []
    for rf in response_files:
        text = rf.read_text(encoding="utf-8")
        # 支持 response 文件是 raw markdown 或 YAML {"output": "..."}
        raw_output = text
        try:
            data = yaml.safe_load(text)
            if isinstance(data, dict) and "output" in data:
                raw_output = data["output"]
        except yaml.YAMLError:
            pass
        buffers = parse_llm_buffers(raw_output, default_source=default_source)
        for buf in buffers:
            written.append(write_buffer(buf, subtype=buf["type"], buffer_dir=buffer_dir))
    return written


@click.command()
@click.option("--root", default=".", help="项目根目录")
@click.option("--deep", is_flag=True, help="深度编译模式")
@click.option("--max-chars", default=30000, help="每批最大字符数")
@click.option("--genres", default="", help='体裁覆盖，格式 "文件名=体裁,..."')
@click.option("--apply", is_flag=True, help="应用 LLM response 写入 Buffer")
@click.option("--plan", is_flag=True, help="只输出编译计划")
def compile_cmd(root, deep, max_chars, genres, apply, plan):
    root_path = Path(root).resolve()
    inbox_dir = root_path / "00-Inbox"
    buffer_dir = root_path / "05-Buffer"
    archive_dir = root_path / "03-Archive"
    tmp_dir = root_path / ".nexogenesis" / "tmp" / "compile"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    if max_chars <= 0:
        raise click.ClickException("--max-chars 必须为正整数")

    docs = scan_inbox(inbox_dir)
    if not docs:
        click.echo("00-Inbox/ 为空，无需编译。")
        return

    try:
        genre_overrides = _parse_genres_arg(genres)
    except click.ClickException:
        raise

    compile_plan = build_compile_plan(docs)

    if plan:
        click.echo("=== /compile 编译计划 ===")
        for item in compile_plan:
            marker = "（LLM 确认）" if item["path"].name in genre_overrides else "（启发式预判）"
            click.echo(f"  {item['path'].name} -> {item['predicted_genre']} {marker}")
        click.echo("=== 计划结束 ===")
        return

    final_genres = {}
    for item in compile_plan:
        final_genres[item["path"].name] = genre_overrides.get(item["path"].name, item["predicted_genre"])

    if deep and len(docs) > DEEP_MODE_DOC_GUARD:
        click.echo(
            f"⚠️  深度编译守卫：Inbox 中有 {len(docs)} 篇文档（>{DEEP_MODE_DOC_GUARD}），"
            "建议普通模式或逐篇深度编译；请与用户确认后继续。",
            err=True,
        )

    ensure_buffer_dirs(buffer_dir)
    units = build_compile_units(docs, max_chars=max_chars, genres=final_genres)
    batches = build_batches(units, max_chars=max_chars)

    if not apply:
        paths = _write_prompts(batches, deep=deep, tmp_dir=tmp_dir)
        click.echo(f"已生成 {len(paths)} 个 prompt 文件：")
        for p in paths:
            click.echo(f"  {p}")
        click.echo("请 Agent 调用 LLM 并将每个 response 保存为同目录的 batch-XXX-response.md，然后运行 --apply。")
        return

    written = _apply_responses(tmp_dir, buffer_dir, default_source="00-Inbox compile")
    errors, warnings = run_validate(root_path)
    if errors:
        raise click.ClickException("Buffer 校验失败：\n" + "\n".join(errors))

    processed = {u["source_path"] for u in units}
    archive_dir.mkdir(parents=True, exist_ok=True)
    for src in processed:
        target = archive_dir / src.name
        counter = 1
        while target.exists():
            target = archive_dir / f"{src.stem}-{counter}{src.suffix}"
            counter += 1
        shutil.move(str(src), str(target))

    journal.append(
        root_path,
        f"compile-{len(written)}",
        "compile",
        [str(w.relative_to(root_path)) for w in written],
        "00-Inbox",
        "user",
    )
    generate_indexes(root_path)
    click.echo(f"Compile applied: {len(written)} buffers written, {len(processed)} docs archived.")
