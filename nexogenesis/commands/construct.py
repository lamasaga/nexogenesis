from pathlib import Path

import click

from nexogenesis import journal
from nexogenesis.commands.write import write_cmd
from nexogenesis.graph.analyze import (
    analyze_graph,
    load_structure_ops,
    merge_structure_signals,
    structure_ops_to_signals,
    write_structure_ops_batch_draft,
)
from nexogenesis.ingest.batch_auto import (
    load_batch_data,
    self_check_batch,
    stamp_approved_by,
    suggest_lenses,
    write_construct_runbook,
)
from nexogenesis.ingest.buffer_status import (
    load_buffer_paths_by_status,
    resolve_consumed_buffers,
    set_buffer_status,
)
from nexogenesis.ingest.context_pack import (
    DEFAULT_LENS_BUFFERS,
    DEFAULT_LENS_CARDS,
    card_catalog,
    load_buffer_records,
    load_cards_by_ids,
)
from nexogenesis.ingest.prompts import render_construct_prompt
from nexogenesis.ingest.structure_signals import (
    LENSES,
    collect_structure_signals,
    index_all_buffers,
    render_diagnose_report,
    suggest_ids_for_lens,
)
from nexogenesis.operations import BatchOperation
from nexogenesis.store import Store
from nexogenesis.yaml_utils import atomic_write_file


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


def _run_construct_apply(
    root_path: Path,
    batch_path: Path,
    buffer_dir: Path,
    *,
    approved_by: str,
) -> None:
    ctx = click.Context(write_cmd)
    ctx.invoke(write_cmd, batch=str(batch_path), root=str(root_path))

    digested = load_buffer_paths_by_status(buffer_dir, "digested")
    batch_op = BatchOperation.from_file(batch_path)
    consumed = resolve_consumed_buffers(root_path, batch_op, digested)
    marked = 0
    for p in consumed:
        if set_buffer_status(p, "digested", "constructed"):
            marked += 1

    write_ids = [
        w.get("id") for w in batch_op.writes if isinstance(w, dict) and w.get("id")
    ]
    journal.append(
        root_path,
        "construct",
        "construct",
        write_ids or [f"marked-{marked}"],
        "01-Cards + 05-Buffer",
        approved_by,
    )
    click.echo(f"Construct applied. Marked {marked} buffer(s) constructed.")


def _auto_apply_batch(root_path: Path, batch_path: Path, buffer_dir: Path) -> None:
    try:
        data = load_batch_data(batch_path)
    except Exception as exc:
        raise click.ClickException(f"batch 无法解析: {exc}") from exc
    errors = self_check_batch(
        data, mode="construct", bootstrap=False, require_approved_by=False
    )
    if errors:
        raise click.ClickException(
            "construct --auto 自检失败：\n- " + "\n- ".join(errors)
        )
    approved = stamp_approved_by(batch_path, "agent")
    click.echo(f"construct --auto 自检通过，approved_by={approved}，开始 apply…")
    _run_construct_apply(root_path, batch_path, buffer_dir, approved_by=approved)


def _run_diagnose(
    root_path: Path,
    store: Store,
    buffer_records: list,
    questions: list[str],
    catalog: list,
    signals: dict,
    tmp_dir: Path,
    *,
    auto: bool,
) -> None:
    if store.cards:
        analyze_graph(root_path, rebuild=True)

    merged = merge_structure_signals(signals, structure_ops_to_signals(load_structure_ops(root_path)))

    report = render_diagnose_report(store, buffer_records, merged)
    graph_summary = root_path / ".nexogenesis" / "graph" / "reports" / "latest-summary.md"
    if graph_summary.exists():
        report += "\n\n---\n\n## 图分析（graph analyze）\n\n"
        report += graph_summary.read_text(encoding="utf-8")

    report_path = tmp_dir / "lenses-report.md"
    atomic_write_file(report_path, report)

    flat_signals = []
    for name in LENSES:
        for s in merged.get(name) or []:
            flat_signals.append(f"[{name}] {s}")

    prompt = render_construct_prompt(
        catalog=catalog,
        buffers=buffer_records,
        questions=questions,
        signals=flat_signals,
        diagnose_mode=True,
    )
    prompt_path = tmp_dir / "diagnose-prompt.md"
    atomic_write_file(prompt_path, prompt)

    ops_draft = write_structure_ops_batch_draft(
        root_path, load_structure_ops(root_path)
    )

    click.echo(f"已生成诊断报告: {report_path}")
    click.echo(f"诊断 prompt（无全文）: {prompt_path}")
    click.echo(f"结构提案草稿: {ops_draft}")

    if auto:
        suggested = suggest_lenses(merged)
        sug_path = tmp_dir / "suggested-lenses.txt"
        atomic_write_file(
            sug_path,
            "\n".join(suggested) + ("\n" if suggested else "# none\n"),
        )
        runbook = write_construct_runbook(
            tmp_dir, suggested=suggested, batch_path=tmp_dir / "batch.yaml"
        )
        click.echo(f"建议镜头: {', '.join(suggested) or '（无）'} → {sug_path}")
        click.echo(f"已写 auto 规程: {runbook}")
        click.echo(
            "AUTO: 按 suggested-lenses 逐个 "
            "`construct --lens <name>` → 写 batch → "
            "`construct --auto --lens <name>`。"
        )
        return

    click.echo(
        "下一步：python -m nexogenesis construct --lens "
        "cluster|distinguish|articulate|cross_source"
    )


@click.command()
@click.option("--root", default=".", help="项目根目录")
@click.option("--diagnose", is_flag=True, help="只生成结构诊断报告（无 Buffer/卡全文）")
@click.option(
    "--lens",
    default=None,
    type=click.Choice(list(LENSES), case_sensitive=False),
    help="按镜头生成 construct prompt（一次一个；禁止 all）",
)
@click.option("--deep-cards", default=DEFAULT_LENS_CARDS, show_default=True, type=int)
@click.option("--wave-buffers", default=DEFAULT_LENS_BUFFERS, show_default=True, type=int)
@click.option("--plan", is_flag=True, help="打印本镜头将深读的对象，不写 prompt")
@click.option("--apply", is_flag=True, help="应用 batch 文件写入卡片")
@click.option(
    "--auto",
    is_flag=True,
    help="Agent 自主模式：诊断+建议镜头；有 lens+batch 则自检后 apply",
)
def construct_cmd(root, diagnose, lens, deep_cards, wave_buffers, plan, apply, auto):
    root_path = Path(root).resolve()
    buffer_dir = root_path / "05-Buffer"
    cards_dir = root_path / "01-Cards"
    profile_path = root_path / "02-Profile" / "问题清单.md"
    tmp_dir = root_path / ".nexogenesis" / "tmp" / "construct"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    if plan and auto:
        raise click.ClickException("--plan 与 --auto 不能同时使用")

    store = Store(cards_dir).load()
    buffer_records = index_all_buffers(buffer_dir, root_path)
    questions = _parse_questions(profile_path)
    catalog = card_catalog(store)
    signals = collect_structure_signals(store, buffer_records)
    batch_path = tmp_dir / "batch.yaml"

    if apply and not auto:
        if not batch_path.exists():
            raise click.ClickException(f"未找到 {batch_path}，请先生成并确认 batch。")
        _run_construct_apply(root_path, batch_path, buffer_dir, approved_by="user")
        return

    if auto and (apply or lens) and batch_path.exists():
        _auto_apply_batch(root_path, batch_path, buffer_dir)
        return

    if diagnose or lens is None:
        _run_diagnose(
            root_path,
            store,
            buffer_records,
            questions,
            catalog,
            signals,
            tmp_dir,
            auto=auto,
        )
        return

    if lens.lower() == "all":
        raise click.ClickException("禁止 --lens all，请一次只跑一个镜头。")

    merged = merge_structure_signals(signals, structure_ops_to_signals(load_structure_ops(root_path)))

    card_ids, buf_paths = suggest_ids_for_lens(
        store,
        buffer_records,
        merged,
        lens.lower(),
        max_cards=deep_cards,
        max_buffers=wave_buffers,
    )

    try:
        from nexogenesis.retrieve.context_package import build_context_package

        pkg = build_context_package(
            root_path,
            query=lens.lower(),
            mode="construct",
            seeds=card_ids,
            graph_nodes=deep_cards,
            rag_top=2,
        )
        for n in pkg.get("structure", {}).get("nodes") or []:
            if n["id"] not in card_ids:
                card_ids.append(n["id"])
    except Exception:
        pass

    deep = load_cards_by_ids(store, card_ids[:deep_cards])
    path_set = set(buf_paths)
    selected_bufs = [b for b in buffer_records if b["path"] in path_set]
    if len(selected_bufs) < len(buf_paths):
        missing = [p for p in buf_paths if p not in {b["path"] for b in selected_bufs}]
        extra_paths = [root_path / mp for mp in missing if (root_path / mp).exists()]
        if extra_paths:
            selected_bufs.extend(load_buffer_records(extra_paths, root_path))

    lens_signals = list(merged.get(lens.lower()) or [])

    if plan:
        click.echo(f"=== /construct lens={lens} ===")
        for c in deep:
            click.echo(f"  [深读卡] {c['id']}")
        for b in selected_bufs:
            click.echo(f"  [Buffer] {b['path']}")
        for s in lens_signals[:15]:
            click.echo(f"  [信号] {s}")
        click.echo("=== 计划结束 ===")
        return

    prompt = render_construct_prompt(
        catalog=catalog,
        deep_cards=deep,
        buffers=selected_bufs,
        questions=questions,
        lens=lens.lower(),
        signals=lens_signals,
        diagnose_mode=False,
    )
    prompt_path = tmp_dir / "prompt.md"
    atomic_write_file(prompt_path, prompt)
    click.echo(f"已生成 construct prompt（lens={lens}）: {prompt_path}")
    click.echo(f"深读卡 {len(deep)}，Buffer {len(selected_bufs)}。")

    if auto:
        runbook = write_construct_runbook(
            tmp_dir,
            suggested=[lens.lower()],
            batch_path=batch_path,
        )
        click.echo(f"已写 auto 规程: {runbook}")
        click.echo(
            f"AUTO: 请生成 batch 到 {batch_path} 后再次运行 "
            f"`python -m nexogenesis construct --auto --lens {lens}`。"
        )
        return

    click.echo(f"请保存 batch 到 {batch_path}，确认后 --apply。")
