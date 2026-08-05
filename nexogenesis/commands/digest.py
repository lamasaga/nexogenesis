from pathlib import Path



import click



from nexogenesis import journal

from nexogenesis.commands.write import write_cmd

from nexogenesis.ingest.batch_auto import (

    load_batch_data,

    self_check_batch,

    stamp_approved_by,

    write_digest_runbook,

)

from nexogenesis.ingest.buffer_status import (

    load_buffer_paths_by_status,

    resolve_consumed_buffers,

    set_buffer_status,

)

from nexogenesis.ingest.context_pack import (

    DEFAULT_DEEP_CARDS,

    DEFAULT_WAVE_BUFFERS,

    card_catalog,

    estimate_pack_chars,

    load_buffer_records,

    read_index_excerpt,

    select_deep_cards,

    select_digest_buffer_wave,

)

from nexogenesis.ingest.prompts import render_digest_prompt
from nexogenesis.retrieve.context_package import (
    build_context_package,
    format_material_excerpt,
    seeds_from_buffers,
)

from nexogenesis.models import CardType

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





@click.command()

@click.option("--root", default=".", help="项目根目录")

@click.option("--status", default="scratch", help="要消化的 Buffer 状态")

@click.option(

    "--wave-buffers",

    default=DEFAULT_WAVE_BUFFERS,

    show_default=True,

    type=int,

    help="本波最多消化的 Buffer 数",

)

@click.option(

    "--deep-cards",

    default=DEFAULT_DEEP_CARDS,

    show_default=True,

    type=int,

    help="注入正文的相关卡片上限",

)

@click.option("--all-scratch", is_flag=True, help="调试：本波吃掉全部指定 status 的 Buffer")

@click.option("--plan", is_flag=True, help="只打印本波选择与预算，不写 prompt")

@click.option("--apply", is_flag=True, help="应用 batch 文件写入卡片")

@click.option(

    "--auto",

    is_flag=True,

    help="Agent 自主模式：无 batch 则生成 prompt+规程；有 batch 则自检通过后 apply",

)

def digest_cmd(root, status, wave_buffers, deep_cards, all_scratch, plan, apply, auto):

    root_path = Path(root).resolve()

    buffer_dir = root_path / "05-Buffer"

    cards_dir = root_path / "01-Cards"

    profile_path = root_path / "02-Profile" / "问题清单.md"

    tmp_dir = root_path / ".nexogenesis" / "tmp" / "digest"

    tmp_dir.mkdir(parents=True, exist_ok=True)



    if plan and auto:

        raise click.ClickException("--plan 与 --auto 不能同时使用")

    if wave_buffers <= 0 and not all_scratch:

        raise click.ClickException("--wave-buffers 必须为正整数（或使用 --all-scratch）")

    if deep_cards < 0:

        raise click.ClickException("--deep-cards 不能为负")



    buffer_paths = load_buffer_paths_by_status(buffer_dir, status)

    batch_path = tmp_dir / "batch.yaml"



    # --auto 且已有 batch：允许在无 scratch 时仍 apply（路径由 consumed_buffers 解析）

    if auto and batch_path.exists():

        store = Store(cards_dir).load()

        bootstrap = not any(c.type == CardType.DOMAIN for c in store.cards.values())

        try:

            data = load_batch_data(batch_path)

        except Exception as exc:

            raise click.ClickException(f"batch 无法解析: {exc}") from exc

        errors = self_check_batch(
            data, mode="digest", bootstrap=bootstrap, require_approved_by=False
        )

        if errors:

            raise click.ClickException(

                "digest --auto 自检失败：\n- " + "\n- ".join(errors)

            )

        approved = stamp_approved_by(batch_path, "agent")

        click.echo(f"digest --auto 自检通过，approved_by={approved}，开始 apply…")

        _run_digest_apply(

            root_path, batch_path, buffer_dir, status, approved_by=approved

        )

        return



    if not buffer_paths and not apply:

        click.echo("没有待消化的 Buffer。")

        return



    store = Store(cards_dir).load()

    all_records = load_buffer_records(buffer_paths, root_path)

    bootstrap = not any(c.type == CardType.DOMAIN for c in store.cards.values())

    selected, deferred = select_digest_buffer_wave(

        all_records, max_buffers=wave_buffers, all_scratch=all_scratch, bootstrap=bootstrap

    )

    catalog = card_catalog(store)

    deep = select_deep_cards(store, selected, max_deep=deep_cards, root=root_path)

    questions = _parse_questions(profile_path)

    index_excerpts = "\n".join(

        x

        for x in (

            read_index_excerpt(root_path, "domain-index.md"),

            read_index_excerpt(root_path, "conflict-index.md"),

        )

        if x

    )

    est = estimate_pack_chars(

        catalog_lines=[c["line"] for c in catalog],

        deep_cards=deep,

        buffers=selected,

        extra=index_excerpts,

    )



    if plan:

        click.echo("=== /digest 分波计划 ===")
        n = len(selected)
        suggest_new = max(2, n // 3) if n else 0
        click.echo(
            f"status={status} selected={n} deferred={len(deferred)} "
            f"deep_cards={len(deep)} bootstrap={bootstrap} est_chars≈{est}"
        )
        click.echo(
            f"质量提示：本波 {n} 片 Buffer → 建议新建 Card ≤ {suggest_new}，"
            "其余 enrich/skip；digest 主职是聚合涌现，不是逐片转卡。"
        )
        for b in selected:
            click.echo(f"  [本波] {b['role']} {b['path']}")
        for b in deferred[:20]:
            click.echo(f"  [暂缓] {b['path']}")
        if len(deferred) > 20:
            click.echo(f"  ... 另有 {len(deferred) - 20} 片暂缓")
        for c in deep:
            click.echo(f"  [深读] {c['id']} ({c['type']})")
        # Domain 健康度：把「该不该分裂」变成可观测信号
        domain_cards = [c for c in store.cards.values() if c.type == CardType.DOMAIN]
        for dc in sorted(domain_cards, key=lambda c: c.id):
            attached = sum(
                1
                for c in store.cards.values()
                if c.type != CardType.DOMAIN and dc.id in (c.domains or [])
            )
            n_rel = len(dc.relations or [])
            n_body = len(dc.body or "")
            overloaded = attached > 25 or n_rel > 12 or n_body > 3000
            line = (
                f"  [domain健康] {dc.id}: 挂靠={attached} "
                f"relations={n_rel} body≈{n_body}字"
            )
            if overloaded:
                line += " ⚠ domain_overloaded（考虑分裂 sibling domain，见 digest prompt 判定）"
            click.echo(line)
        if len(domain_cards) == 1 and not bootstrap:
            total_attached = sum(
                1
                for c in store.cards.values()
                if c.type != CardType.DOMAIN and domain_cards[0].id in (c.domains or [])
            )
            if total_attached > 0:
                click.echo(
                    "  提示：库内仅 1 张 domain。若本波质料的核心问题无法被其覆盖，"
                    "允许新建 sibling domain（勿把一切挂同一张）。"
                )
        click.echo("=== 计划结束 ===")
        return


    if apply:

        if not batch_path.exists():

            raise click.ClickException(f"未找到 {batch_path}，请先生成并确认 batch。")

        _run_digest_apply(

            root_path, batch_path, buffer_dir, status, approved_by="user"

        )

        return



    if not buffer_paths:

        click.echo("没有待消化的 Buffer。")

        return



    if batch_path.exists():
        click.echo(
            f"WARNING: {batch_path} 已存在。若上次 apply 失败，请先修 batch 再 --apply；"
            "重新生成本波 prompt 前请自行备份 batch，避免已修好的内容被覆盖。"
        )

    material_excerpts = ""
    try:
        btokens = seeds_from_buffers(selected)
        query = " ".join(sorted(btokens)[:24]) or " ".join(
            b.get("title", "") for b in selected[:3]
        )
        pkg = build_context_package(
            root_path,
            query=query,
            mode="digest",
            buffer_tokens=btokens,
            use_graph=False,
            rag_top=6,
        )
        material_excerpts = format_material_excerpt(pkg.get("material") or [], max_items=6)
    except Exception:
        pass

    prompt = render_digest_prompt(

        selected,

        catalog=catalog,

        deep_cards=deep,

        questions=questions,

        bootstrap=bootstrap,

        deferred_count=len(deferred),

        index_excerpts=index_excerpts,

        material_excerpts=material_excerpts,

    )

    prompt_path = tmp_dir / "prompt.md"

    atomic_write_file(prompt_path, prompt)

    click.echo(f"已生成 digest prompt: {prompt_path}")

    click.echo(

        f"本波 {len(selected)}/{len(all_records)} Buffer，深读 {len(deep)} 卡，"

        f"est_chars≈{est}，暂缓 {len(deferred)}"

    )

    if bootstrap:

        click.echo("提示：空库/无 domain — batch 须先写 domain 再写实例卡。")



    if auto:

        runbook = write_digest_runbook(

            tmp_dir, batch_path=batch_path, prompt_path=prompt_path

        )

        click.echo(f"已写 auto 规程: {runbook}")

        click.echo(

            f"AUTO: 请生成 batch 到 {batch_path} 后再次运行 "

            "`python -m nexogenesis digest --auto`（自检通过即写入）。"

        )

        return



    click.echo(

        f"请 Agent 调用 LLM 并将 batch YAML 保存到 {batch_path}；"

        "请在 operation.consumed_buffers 列出实际消费的 Buffer 相对路径，确认后运行 --apply。"

    )





def _run_digest_apply(

    root_path: Path,

    batch_path: Path,

    buffer_dir: Path,

    status: str,

    *,

    approved_by: str,

) -> None:

    ctx = click.Context(write_cmd)

    ctx.invoke(write_cmd, batch=str(batch_path), root=str(root_path))



    batch_op = BatchOperation.from_file(batch_path)

    # 消费解析仍允许命中本 status 全部路径（含本波外，若用户显式写入）

    buffer_paths = load_buffer_paths_by_status(buffer_dir, status)

    consumed = resolve_consumed_buffers(root_path, batch_op, buffer_paths)

    if not consumed:

        click.echo(

            "WARNING: batch 未匹配到 consumed Buffer；未修改任何 Buffer status。"

            "请在 operation.consumed_buffers 中声明路径。"

        )

    marked = 0

    for p in consumed:

        if set_buffer_status(p, status, "digested"):

            marked += 1



    journal.append(

        root_path,

        f"digest-{marked}",

        "digest",

        [str(p.relative_to(root_path)) for p in consumed],

        "05-Buffer",

        approved_by,

    )

    click.echo(f"Digest applied: {marked} buffers consumed.")


