from pathlib import Path

from click.testing import CliRunner

from nexogenesis.commands.init import init_cmd
from nexogenesis.commands.memory import attention_cmd, memory_cmd, signal_cmd
from nexogenesis.retrieve.context_package import build_context_package
from nexogenesis.thinking.assemble import assemble_working_set
from nexogenesis.thinking.config import (
    deep_merge,
    load_attention_config,
    resolve_effective_config,
    validate_attention_config,
)
from nexogenesis.thinking.signals import evaluate_strong_signals
from nexogenesis.thinking.stm import STMStore


def _domain_and_conflict(cards: Path):
    (cards / "教学.md").write_text(
        "---\nid: 教学\ntitle: 教学\ntype: domain\nmaturity: growing\n"
        "lifecycle: active\ndomains: [教学]\norigin: user\nsources: []\nrelations: []\n"
        "created: '2026-07-24'\nupdated: '2026-07-24'\n---\n\n## 核心问题\n\n　　教学。\n",
        encoding="utf-8",
    )
    (cards / "主张甲.md").write_text(
        "---\nid: 主张甲\ntitle: 主张甲\ntype: claim\nmaturity: growing\n"
        "lifecycle: active\ndomains: [教学]\norigin: user\nsources: []\n"
        "relations:\n  - target: 主张乙\n    type: conflicts-with\n    note: 对立\n"
        "created: '2026-07-24'\nupdated: '2026-07-24'\n---\n\n"
        "## 一句话主张\n\n　　反馈应极简。\n",
        encoding="utf-8",
    )
    (cards / "主张乙.md").write_text(
        "---\nid: 主张乙\ntitle: 主张乙\ntype: claim\nmaturity: growing\n"
        "lifecycle: active\ndomains: [教学]\norigin: document\nsources: []\n"
        "relations:\n  - target: 主张甲\n    type: conflicts-with\n    note: 对立\n"
        "created: '2026-07-24'\nupdated: '2026-07-24'\n---\n\n"
        "## 一句话主张\n\n　　反馈应详尽。\n",
        encoding="utf-8",
    )
    (cards / "冲突卡.md").write_text(
        "---\nid: 冲突卡\ntitle: 详略冲突\ntype: conflict\nmaturity: seed\n"
        "lifecycle: active\ndomains: [教学]\norigin: system\nsources: []\n"
        "relations:\n  - target: 主张甲\n    type: involves\n    note: a\n"
        "  - target: 主张乙\n    type: involves\n    note: b\n"
        "created: '2026-07-24'\nupdated: '2026-07-24'\n---\n\n"
        "## 对立双方\n\n　　详与略。\n",
        encoding="utf-8",
    )


def test_attention_load_and_validate(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cfg = load_attention_config(tmp_path)
    errors, _ = validate_attention_config(cfg)
    assert not errors
    assert cfg.get("stm", {}).get("max_sessions") == 10
    eff = resolve_effective_config(cfg, profile="judge")
    assert eff["slots"]["conflict"] == 3


def test_attention_project_override(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    override = tmp_path / ".nexogenesis" / "attention.yaml"
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text(
        "slots:\n  expansion: 9\n  conflict: 1\n",
        encoding="utf-8",
    )
    cfg = load_attention_config(tmp_path)
    assert cfg["slots"]["expansion"] == 9
    assert cfg["slots"]["conflict"] == 1


def test_deep_merge():
    a = {"slots": {"core": 1, "expansion": 2}, "x": 1}
    b = {"slots": {"expansion": 5}, "y": 2}
    m = deep_merge(a, b)
    assert m["slots"]["core"] == 1
    assert m["slots"]["expansion"] == 5
    assert m["y"] == 2


def test_stm_roll_ten_sessions(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    store = STMStore(tmp_path)
    for i in range(12):
        store.start_session(title=f"s{i}")
        store.update_slots(focus=f"焦点{i}", cite=[f"卡{i}"])
        store.end_session()
    index = store.load_index()
    assert len(index["sessions"]) <= 10


def test_stm_cross_session_context(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    store = STMStore(tmp_path)
    store.start_session(title="旧")
    store.update_slots(focus="有效反思", add_tension="完整 vs 低成本", cite=["教学"])
    store.end_session()
    store.start_session(title="新")
    store.update_slots(focus="反馈差距")
    ctx = store.attention_context()
    assert "教学" in ctx["all_cited"]
    assert any("完整" in t for t in ctx["all_tensions"])
    assert "反馈差距" in ctx["focus_tokens"] or ctx["slots"]["focus"] == "反馈差距"


def test_assemble_dual_accounts(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    _domain_and_conflict(tmp_path / "01-Cards")
    from nexogenesis.graph.build import rebuild_graph

    rebuild_graph(tmp_path)
    store = STMStore(tmp_path)
    store.start_session(title="t")
    store.update_slots(focus="反馈", cite=["主张甲"], add_tension="详略对立")

    pkg = assemble_working_set(tmp_path, query="反馈 对立", mode="talk")
    accounts = pkg["structure"]["accounts"]
    assert accounts.get("core") or accounts.get("expansion") or accounts.get("conflict")
    # conflict 账户应尽量占到席（有 conflicts-with / conflict 卡）
    nodes = pkg["structure"]["nodes"]
    assert nodes
    assert any(n.get("account") for n in nodes)


def test_retrieve_uses_attention(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    _domain_and_conflict(tmp_path / "01-Cards")
    from nexogenesis.graph.build import rebuild_graph

    rebuild_graph(tmp_path)
    pkg = build_context_package(tmp_path, query="教学反馈", mode="talk")
    assert "accounts" in pkg["structure"]
    assert pkg.get("attention")


def test_strong_signals_capture_and_inbox(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cfg = load_attention_config(tmp_path)
    eff = resolve_effective_config(cfg)
    slots = {"turn": 0, "capture_prompts": 0, "last_signal_turn": -999}

    sigs = evaluate_strong_signals("请记一下刚才那句", stm_slots=slots, config=eff)
    assert any(s["type"] == "capture" for s in sigs)

    sigs2 = evaluate_strong_signals(
        "Inbox 里那篇论文要不要处理", stm_slots=slots, config=eff
    )
    assert any(s["type"] == "suggest_compile" for s in sigs2)


def test_session_override_cli(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    r = runner.invoke(memory_cmd, ["start", "--root", str(tmp_path), "--title", "x"])
    assert r.exit_code == 0, r.output
    r = runner.invoke(
        memory_cmd,
        ["override", "--root", str(tmp_path), "--conflict", "4", "--expansion", "3"],
    )
    assert r.exit_code == 0, r.output
    store = STMStore(tmp_path)
    ov = store.get_session_overrides()
    assert ov["slots"]["conflict"] == 4
    assert ov["slots"]["expansion"] == 3

    cfg = load_attention_config(tmp_path)
    eff = resolve_effective_config(cfg, profile="talk", session_overrides=ov)
    assert eff["slots"]["conflict"] == 4


def test_attention_and_signal_cli(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    r = runner.invoke(attention_cmd, ["validate", "--root", str(tmp_path)])
    assert r.exit_code == 0, r.output
    r = runner.invoke(
        signal_cmd, ["--root", str(tmp_path), "--text", "记一下", "--bump-turn"]
    )
    assert r.exit_code == 0, r.output
    assert "capture" in r.output
