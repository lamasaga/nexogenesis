from pathlib import Path

import click
import yaml

from nexogenesis.thinking.config import (
    load_attention_config,
    resolve_effective_config,
    validate_attention_config,
)
from nexogenesis.thinking.signals import evaluate_strong_signals
from nexogenesis.thinking.stm import STMStore
from nexogenesis.yaml_utils import atomic_write_file


@click.group()
def memory_cmd():
    """短期记忆（STM）与会话覆盖。"""
    pass


@memory_cmd.command("start")
@click.option("--root", default=".", help="项目根目录")
@click.option("--title", default="", help="会话标题")
def memory_start(root: str, title: str):
    store = STMStore(Path(root).resolve())
    session = store.start_session(title=title)
    click.echo(f"session={session['id']} title={session['title']}")


@memory_cmd.command("end")
@click.option("--root", default=".", help="项目根目录")
def memory_end(root: str):
    store = STMStore(Path(root).resolve())
    sid = store.end_session()
    if not sid:
        click.echo("无进行中的会话。")
        return
    click.echo(f"closed={sid}")


@memory_cmd.command("status")
@click.option("--root", default=".", help="项目根目录")
def memory_status(root: str):
    store = STMStore(Path(root).resolve())
    index = store.load_index()
    cur = store.current_session()
    click.echo(f"current={index.get('current_session_id')}")
    click.echo(f"sessions={len(index.get('sessions') or [])} max={store.max_sessions()}")
    if cur:
        slots = cur.get("slots") or {}
        click.echo(f"focus={slots.get('focus')!r}")
        click.echo(f"turn={slots.get('turn')} cited={slots.get('cited_cards')}")
        click.echo(f"tensions={slots.get('tensions')}")
        click.echo(f"overrides={slots.get('session_overrides')}")
        click.echo(f"capture_disabled={slots.get('signals_disabled_capture')}")


@memory_cmd.command("update")
@click.option("--root", default=".", help="项目根目录")
@click.option("--focus", default=None, help="更新焦点")
@click.option("--cite", multiple=True, help="追加已引用卡片 id")
@click.option("--tension", default=None, help="追加张力")
@click.option("--claim-user", default=None, help="追加用户主张")
@click.option("--claim-system", default=None, help="追加系统主张")
@click.option("--directive", default=None, help="追加用户禁令/指令")
@click.option("--bridge", default=None, help="追加桥接提示卡 id")
@click.option("--bump-turn", is_flag=True, help="回合 +1")
def memory_update(
    root,
    focus,
    cite,
    tension,
    claim_user,
    claim_system,
    directive,
    bridge,
    bump_turn,
):
    store = STMStore(Path(root).resolve())
    session = store.update_slots(
        focus=focus,
        cite=list(cite) if cite else None,
        add_tension=tension,
        add_claim_user=claim_user,
        add_claim_system=claim_system,
        add_directive=directive,
        add_bridge_hint=bridge,
        bump_turn=bump_turn,
    )
    click.echo(f"updated session={session['id']} turn={session['slots'].get('turn')}")


@memory_cmd.command("override")
@click.option("--root", default=".", help="项目根目录")
@click.option("--conflict", default=None, type=int, help="本会话 conflict 席位")
@click.option("--expansion", default=None, type=int, help="本会话 expansion 席位")
@click.option("--core", default=None, type=int, help="本会话 core 席位")
@click.option("--clear", is_flag=True, help="清除会话覆盖")
@click.option("--note", default="", help="覆盖说明")
def memory_override(root, conflict, expansion, core, clear, note):
    store = STMStore(Path(root).resolve())
    if clear:
        store.clear_session_overrides()
        click.echo("session overrides cleared")
        return
    slots: dict = {}
    if core is not None:
        slots["core"] = core
    if expansion is not None:
        slots["expansion"] = expansion
    if conflict is not None:
        slots["conflict"] = conflict
    overrides: dict = {}
    if slots:
        overrides["slots"] = slots
    if note:
        overrides["note"] = note
    if not overrides:
        raise click.ClickException("请提供 --conflict/--expansion/--core 或 --clear")
    store.set_session_overrides(overrides)
    click.echo(f"overrides={overrides}")


@click.group()
def attention_cmd():
    """注意力配置查看与校验。"""
    pass


@attention_cmd.command("show")
@click.option("--root", default=".", help="项目根目录")
@click.option("--profile", default=None, help="指定 profile（默认 active_profile）")
@click.option("--print-yaml", is_flag=True, help="打印完整有效配置")
def attention_show(root: str, profile: str | None, print_yaml: bool):
    root_path = Path(root).resolve()
    raw = load_attention_config(root_path)
    stm = STMStore(root_path, config=raw)
    overrides = stm.get_session_overrides()
    effective = resolve_effective_config(
        raw, profile=profile, session_overrides=overrides
    )
    errors, warnings = validate_attention_config(raw)
    for w in warnings:
        click.echo(f"WARNING: {w}")
    for e in errors:
        click.echo(f"ERROR: {e}")
    click.echo(f"profile={effective.get('resolved_profile')}")
    click.echo(f"slots={effective.get('slots')}")
    click.echo(f"budget={effective.get('budget')}")
    click.echo(f"session_overrides={overrides or {}}")
    if print_yaml:
        click.echo(yaml.safe_dump(effective, allow_unicode=True, sort_keys=False))


@attention_cmd.command("validate")
@click.option("--root", default=".", help="项目根目录")
def attention_validate(root: str):
    raw = load_attention_config(Path(root).resolve())
    errors, warnings = validate_attention_config(raw)
    for w in warnings:
        click.echo(f"WARNING: {w}")
    if errors:
        for e in errors:
            click.echo(f"ERROR: {e}")
        raise click.ClickException("attention 配置校验失败")
    click.echo("attention: OK")


@click.command("signal")
@click.option("--root", default=".", help="项目根目录")
@click.option("--text", required=True, help="用户本轮文本")
@click.option("--bump-turn", is_flag=True, help="评估前回合 +1")
def signal_cmd(root: str, text: str, bump_turn: bool):
    """评估强信号（只打印建议，不写入卡片）。"""
    root_path = Path(root).resolve()
    cfg = load_attention_config(root_path)
    effective = resolve_effective_config(cfg)
    stm = STMStore(root_path, config=cfg)
    if bump_turn:
        stm.update_slots(bump_turn=True)
    session = stm.require_current()
    slots = session.get("slots") or {}

    # 处理「先别记」
    if "先别记" in text or "别捕获" in text:
        stm.update_slots(add_directive=text, disable_capture_prompts=True)
        slots = stm.require_current()["slots"]

    signals = evaluate_strong_signals(
        text, stm_slots=slots, config=effective
    )
    if not signals:
        click.echo("signals=[]")
        return

    for s in signals:
        click.echo(f"[{s['type']}] {s['prompt']}  # {s['reason']}")

    # 记录冷却与捕获提问计数（主动捕获类）
    capture_like = {"capture", "conflict_draft", "profile_question"}
    if any(s["type"] in capture_like for s in signals):
        if any(s["reason"] == "explicit_capture_phrase" for s in signals):
            stm.update_slots(mark_signal_turn=True)
        else:
            stm.update_slots(increment_capture_prompt=True, mark_signal_turn=True)
    elif signals:
        stm.update_slots(mark_signal_turn=True)

    out = root_path / ".nexogenesis" / "tmp" / "retrieve" / "signals.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_file(
        out, yaml.safe_dump({"text": text, "signals": signals}, allow_unicode=True)
    )
    click.echo(f"已写入: {out}")
