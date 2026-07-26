import json
import shutil
from pathlib import Path

import click

from nexogenesis import journal
from nexogenesis.commands.index import generate_indexes
from nexogenesis.commands.validate import run_validate
from nexogenesis.ingest import ensure_buffer_dirs
from nexogenesis.ingest.batch_runner import (
    check_response_file,
    format_batch_prompt,
    write_buffer,
)
from nexogenesis.ingest.chunker import build_compile_units
from nexogenesis.ingest.compile_planner import (
    DEFAULT_MAX_CHARS,
    DEFAULT_WAVE_DOCS,
    DEFAULT_WAVE_PROMPTS,
    MANIFEST_NAME,
    build_inventory,
    clear_source_progress,
    filter_pending_units,
    format_plan_report,
    load_progress,
    load_wave_manifest,
    mark_manifest_applied,
    mark_units_completed,
    resolve_policy,
    save_progress,
    select_wave,
    write_wave_manifest,
)
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
    for old in tmp_dir.glob("batch-*-prompt.md"):
        try:
            old.unlink()
        except OSError:
            pass
    paths = []
    for idx, batch in enumerate(batches, 1):
        genre = batch[0].get("genre") or "generic"
        prompt = format_batch_prompt(batch, genre=genre, deep=deep)
        p = tmp_dir / f"batch-{idx:03d}-{genre}-prompt.md"
        atomic_write_file(p, prompt)
        paths.append(p)
    return paths


def _response_to_prompt_name(response_name: str) -> str:
    # batch-001-scrap-response.md -> batch-001-scrap-prompt.md
    if "-response." in response_name:
        return response_name.replace("-response.", "-prompt.", 1)
    stem = Path(response_name).stem
    if stem.endswith("-response"):
        return stem[: -len("-response")] + "-prompt.md"
    return response_name


def _list_response_files(tmp_dir: Path, response: str | None) -> list[Path]:
    if response:
        p = Path(response)
        if not p.is_absolute():
            cand = tmp_dir / p.name
            p = cand if cand.exists() else (Path.cwd() / p)
        if not p.exists():
            raise click.ClickException(f"response 文件不存在：{response}")
        return [p.resolve()]
    files = sorted(tmp_dir.glob("batch-*-response.*"))
    # 忽略明显草稿
    files = [f for f in files if not f.name.endswith(("-blocks.md", "-fragments.json"))]
    return files


def _archive_doc(src: Path, archive_dir: Path) -> Path:
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / src.name
    counter = 1
    while target.exists():
        target = archive_dir / f"{src.stem}-{counter}{src.suffix}"
        counter += 1
    shutil.move(str(src), str(target))
    return target


def _check_responses(tmp_dir: Path, *, strict_body: bool) -> int:
    files = _list_response_files(tmp_dir, None)
    if not files:
        click.echo("未找到 batch-*-response.* 文件。")
        return 1
    hard_total = 0
    soft_total = 0
    for rf in files:
        buffers, hard, soft = check_response_file(rf, strict_body=strict_body)
        if hard:
            hard_total += len(hard)
            click.echo(f"FAIL {rf.name}（{len(buffers)} 块）")
            for e in hard:
                click.echo(f"  ERROR: {e}")
        else:
            click.echo(f"OK   {rf.name}（{len(buffers)} 块）")
        for w in soft:
            soft_total += 1
            click.echo(f"  WARNING: {w}")
    click.echo(f"检查结束：{len(files)} 个文件，hard={hard_total}，warning={soft_total}")
    return 1 if hard_total else 0


def _apply_wave(
    *,
    root_path: Path,
    tmp_dir: Path,
    buffer_dir: Path,
    inbox_dir: Path,
    archive_dir: Path,
    strict_body: bool,
    response: str | None,
) -> None:
    try:
        manifest = load_wave_manifest(tmp_dir)
    except FileNotFoundError as e:
        raise click.ClickException(str(e)) from e

    if manifest.get("status") == "applied" and not response:
        raise click.ClickException(
            f"{MANIFEST_NAME} 已 applied。请先运行 compile 生成新一波 prompt。"
        )

    response_files = _list_response_files(tmp_dir, response)
    if not response_files:
        raise click.ClickException(
            "未找到 LLM response 文件。请保存为 "
            ".nexogenesis/tmp/compile/batch-XXX-response.md 后重试。"
        )

    applied_batch_files = set(manifest.get("applied_batch_files") or [])
    all_written: list[Path] = []
    failed: list[str] = []
    succeeded_responses: list[Path] = []

    for rf in response_files:
        buffers, hard, soft = check_response_file(rf, strict_body=strict_body)
        for w in soft:
            click.echo(f"WARNING: {w}")
        if hard:
            failed.append(rf.name)
            for e in hard:
                click.echo(f"ERROR: {e}")
            click.echo(f"跳过 {rf.name}（结构错误，不拖垮其它文件）")
            continue

        written_here: list[Path] = []
        try:
            for buf in buffers:
                written_here.append(
                    write_buffer(buf, subtype=buf["role"], buffer_dir=buffer_dir)
                )
            # 全库校验：仅把槽缺失当 warning；其它错误则回滚本文件写入
            errors, warnings = run_validate(
                root_path, buffer_body_as_errors=strict_body
            )
            # 只关心本轮新写入相关的硬错误
            related = []
            written_set = {p.resolve() for p in written_here}
            for e in errors:
                # 粗匹配：错误路径包含 05-Buffer
                if "05-Buffer" in e:
                    related.append(e)
            # 若存在与 Buffer 相关的 schema/链接错误，回滚本文件
            if related and strict_body:
                raise RuntimeError("\n".join(related))
            # 非 strict：过滤掉仅语义槽类（已在 buffer_body_as_errors=False 时进 warning）
            hard_related = [e for e in errors if "缺少语义槽" not in e and "05-Buffer" in e]
            if hard_related:
                raise RuntimeError("\n".join(hard_related))

            for w in warnings:
                if any(p.name in w for p in written_here):
                    click.echo(f"WARNING: {w}")

            all_written.extend(written_here)
            succeeded_responses.append(rf)
            prompt_name = _response_to_prompt_name(rf.name)
            applied_batch_files.add(prompt_name)
            click.echo(f"OK {rf.name} → {len(written_here)} buffers")
        except Exception as e:
            for p in written_here:
                try:
                    p.unlink(missing_ok=True)
                except OSError:
                    pass
            failed.append(rf.name)
            click.echo(f"ERROR: {rf.name} 写入后校验失败，已回滚该文件写入：{e}")

    # 删除成功的 response，保留失败的供重跑
    for rf in succeeded_responses:
        try:
            rf.unlink()
        except OSError:
            pass

    manifest["applied_batch_files"] = sorted(applied_batch_files)
    manifest["failed_responses"] = failed
    (tmp_dir / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    expected = set(manifest.get("batch_files") or [])
    wave_complete = bool(expected) and expected.issubset(applied_batch_files)

    archived: list[str] = []
    if wave_complete and all_written:
        progress = load_progress(tmp_dir)
        for doc in manifest.get("docs") or []:
            name = doc.get("name")
            unit_ids = list(doc.get("unit_ids") or [])
            if not name:
                continue
            mark_units_completed(progress, name, unit_ids)
            src = Path(doc.get("path") or (inbox_dir / name))
            if not src.exists():
                src = inbox_dir / name
            if not src.exists():
                continue
            policy = manifest.get("policy") or {}
            mc = int(policy.get("max_chars") or DEFAULT_MAX_CHARS)
            genre = doc.get("genre") or "generic"
            doc_type = doc.get("doc_type") or (
                "pdf" if src.suffix.lower() == ".pdf" else "text"
            )
            units = build_compile_units(
                [{"path": src, "doc_type": doc_type}],
                max_chars=mc,
                genres={name: genre},
            )
            pending = filter_pending_units(units, progress)
            if not pending:
                _archive_doc(src, archive_dir)
                clear_source_progress(progress, name)
                archived.append(name)
        save_progress(tmp_dir, progress)
        mark_manifest_applied(tmp_dir, manifest)

    if all_written:
        journal.append(
            root_path,
            f"compile-{len(all_written)}",
            "compile",
            [str(w.relative_to(root_path)) for w in all_written],
            "00-Inbox",
            "user",
        )
        generate_indexes(root_path)

    click.echo(
        f"Compile apply: wrote={len(all_written)} buffers, "
        f"ok_files={len(succeeded_responses)}, failed_files={len(failed)}, "
        f"archived={len(archived)}, wave_complete={wave_complete}"
    )
    if failed and not all_written:
        raise click.ClickException(
            "全部 response 失败，未写入 Buffer：" + ", ".join(failed)
        )
    if failed:
        click.echo(
            "部分 response 失败，已保留失败文件供重跑：" + ", ".join(failed),
            err=True,
        )


@click.command()
@click.option("--root", default=".", help="项目根目录")
@click.option("--deep", is_flag=True, help="深度编译模式（每波 1 篇）")
@click.option(
    "--max-chars",
    default=None,
    type=int,
    help=f"每批最大等效中文字符（默认 {DEFAULT_MAX_CHARS}，deep 默认更小）",
)
@click.option(
    "--wave-prompts",
    default=None,
    type=int,
    help=f"每波最多生成的 prompt 数（默认 {DEFAULT_WAVE_PROMPTS}）",
)
@click.option(
    "--wave-docs",
    default=None,
    type=int,
    help=f"每波最多文档数（默认 {DEFAULT_WAVE_DOCS}）",
)
@click.option("--all", "process_all", is_flag=True, help="关闭分波，处理 Inbox 全部待编译单元")
@click.option("--recursive", is_flag=True, help="递归扫描 00-Inbox 子目录")
@click.option("--genres", default="", help='体裁覆盖，格式 "文件名=体裁,..."')
@click.option("--apply", is_flag=True, help="应用 LLM response 写入 Buffer（按文件部分成功）")
@click.option(
    "--response",
    default=None,
    help="只检查/apply 指定的 response 文件（路径或文件名）",
)
@click.option(
    "--check-responses",
    is_flag=True,
    help="检查 batch-*-response.*，不写盘、不动 Inbox",
)
@click.option(
    "--strict-body",
    is_flag=True,
    help="语义槽缺失视为错误（默认仅 warning，仍可落盘）",
)
@click.option("--plan", is_flag=True, help="只输出分波编译计划")
def compile_cmd(
    root,
    deep,
    max_chars,
    wave_prompts,
    wave_docs,
    process_all,
    recursive,
    genres,
    apply,
    response,
    check_responses,
    strict_body,
    plan,
):
    root_path = Path(root).resolve()
    inbox_dir = root_path / "00-Inbox"
    buffer_dir = root_path / "05-Buffer"
    archive_dir = root_path / "03-Archive"
    tmp_dir = root_path / ".nexogenesis" / "tmp" / "compile"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    if max_chars is not None and max_chars <= 0:
        raise click.ClickException("--max-chars 必须为正整数")
    if wave_prompts is not None and wave_prompts <= 0:
        raise click.ClickException("--wave-prompts 必须为正整数")
    if wave_docs is not None and wave_docs <= 0:
        raise click.ClickException("--wave-docs 必须为正整数")

    if check_responses:
        if response:
            files = _list_response_files(tmp_dir, response)
            buffers, hard, soft = check_response_file(files[0], strict_body=strict_body)
            for e in hard:
                click.echo(f"ERROR: {e}")
            for w in soft:
                click.echo(f"WARNING: {w}")
            click.echo(f"{files[0].name}: {len(buffers)} 块, hard={len(hard)}, warn={len(soft)}")
            if hard:
                raise click.ClickException("检查未通过。")
            return
        code = _check_responses(tmp_dir, strict_body=strict_body)
        if code:
            raise click.ClickException("检查未通过。")
        return

    if apply:
        _apply_wave(
            root_path=root_path,
            tmp_dir=tmp_dir,
            buffer_dir=buffer_dir,
            inbox_dir=inbox_dir,
            archive_dir=archive_dir,
            strict_body=strict_body,
            response=response,
        )
        return

    docs = scan_inbox(inbox_dir, recursive=recursive)
    if not docs:
        click.echo("00-Inbox/ 为空，无需编译。")
        return

    try:
        genre_overrides = _parse_genres_arg(genres)
    except click.ClickException:
        raise

    compile_plan = build_compile_plan(docs)
    final_genres = {}
    for item in compile_plan:
        final_genres[item["path"].name] = genre_overrides.get(
            item["path"].name, item["predicted_genre"]
        )

    policy = resolve_policy(
        deep=deep,
        max_chars=max_chars,
        wave_prompts=wave_prompts,
        wave_docs=wave_docs,
        process_all=process_all,
    )
    inventory = build_inventory(compile_plan, final_genres)
    progress = load_progress(tmp_dir)

    if plan:
        click.echo(format_plan_report(inventory, policy, progress))
        return

    if deep and len(docs) > DEEP_MODE_DOC_GUARD and not process_all:
        click.echo(
            f"⚠️  深度编译守卫：Inbox 中有 {len(docs)} 篇文档（>{DEEP_MODE_DOC_GUARD}），"
            "deep 模式每波仅 1 篇；建议确认后继续或去掉 --deep。",
            err=True,
        )

    ensure_buffer_dirs(buffer_dir)
    wave = select_wave(inventory, policy, progress)
    if not wave.batches:
        click.echo("没有待编译单元（可能均已在 progress 中完成）。可检查 progress.json 或 Inbox。")
        return

    paths = _write_prompts(wave.batches, deep=deep, tmp_dir=tmp_dir)
    manifest_path = write_wave_manifest(
        tmp_dir,
        wave,
        batch_files=[p.name for p in paths],
    )

    click.echo(
        f"本波 {len(wave.selected)}/{len(inventory)} 文档 → {len(paths)} 个 prompt "
        f"(max_chars={policy.max_chars}, wave_prompts≤{policy.wave_prompts})"
    )
    click.echo(f"manifest: {manifest_path}")
    for p in paths:
        click.echo(f"  {p}")
    if wave.remaining_inbox:
        click.echo(f"Inbox 约剩余 {wave.remaining_inbox} 篇/未完成源，本波 --apply 后可再跑 compile。")
    click.echo(
        "请用单代理串行生成 batch-XXX-response.md（默认勿并行子代理）；"
        "每写完一个可先：python -m nexogenesis compile --check-responses；"
        "再 compile --apply（可加 --response <file> 逐个落盘）。"
    )
