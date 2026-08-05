from pathlib import Path

from click.testing import CliRunner

from nexogenesis.commands.construct import construct_cmd
from nexogenesis.commands.init import init_cmd
from nexogenesis.ingest.construct_ops import (
    build_seed_link_writes,
    build_structure_action_plan,
    find_hub_term_candidates,
    find_overloaded_domains,
    suggest_domain_splits,
)
from nexogenesis.ingest.structure_signals import collect_structure_signals
from nexogenesis.store import Store


def _write_card(
    cards: Path,
    cid: str,
    *,
    ctype: str = "claim",
    domains: list[str] | None = None,
    relations: str = "[]",
    title: str | None = None,
) -> None:
    title = title or cid
    domains = domains or ["教学"]
    domains_yaml = "[" + ", ".join(domains) + "]"
    (cards / f"{cid}.md").write_text(
        "---\n"
        f"id: {cid}\n"
        f"title: {title}\n"
        f"type: {ctype}\n"
        "maturity: growing\nlifecycle: active\n"
        f"domains: {domains_yaml}\n"
        "origin: user\nsources: []\n"
        f"relations: {relations}\n"
        "created: '2026-07-24'\nupdated: '2026-07-24'\n"
        "---\n\n"
        "## 主张\n\n　　测试。\n",
        encoding="utf-8",
    )


def test_seed_link_only_empty_relations(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cards = tmp_path / "01-Cards"
    _write_card(cards, "教学", ctype="domain", domains=["教学"])
    _write_card(cards, "空边主张")
    _write_card(
        cards,
        "已有边",
        relations=(
            "[{target: 教学, type: applies-to, note: x}]"
        ),
    )
    store = Store(cards).load()
    writes = build_seed_link_writes(store, today="2026-07-28")
    ids = {w["id"] for w in writes}
    assert "空边主张" in ids
    assert "已有边" not in ids
    assert "教学" not in ids
    rel = writes[0]["relations"][0]
    assert rel["type"] == "applies-to"
    assert rel["target"] == "教学"


def test_involves_and_hub_in_action_plan(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cards = tmp_path / "01-Cards"
    _write_card(cards, "教学", ctype="domain", domains=["教学"])
    _write_card(cards, "主张甲", title="反馈差距甲")
    _write_card(cards, "主张乙", title="反馈差距乙")
    _write_card(cards, "主张丙", title="反馈差距丙")
    _write_card(
        cards,
        "冲突卡",
        ctype="conflict",
        title="反馈冲突",
        relations="[{target: 教学, type: applies-to, note: only-domain}]",
    )
    store = Store(cards).load()
    plan = build_structure_action_plan(store)
    involves = [o for o in plan["ops_need_llm"] if o["op"] == "require_involves"]
    assert any(o["cards"] == ["冲突卡"] for o in involves)
    hubs = find_hub_term_candidates(store, min_count=3)
    assert any(h.get("term") == "反馈差距" for h in hubs)


def test_construct_diagnose_writes_action_artifacts(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cards = tmp_path / "01-Cards"
    _write_card(cards, "教学", ctype="domain", domains=["教学"])
    _write_card(cards, "空边主张")
    result = runner.invoke(construct_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    draft = (
        tmp_path / ".nexogenesis" / "tmp" / "construct" / "structure-ops-draft.md"
    ).read_text(encoding="utf-8")
    assert "可执行" in draft or "seed-links" in draft
    assert "空边主张" in draft
    seed = tmp_path / ".nexogenesis" / "tmp" / "construct" / "structure-seed-links.yaml"
    assert seed.exists()
    assert "空边主张" in seed.read_text(encoding="utf-8")
    assert "可执行结构动作" in (
        tmp_path / ".nexogenesis" / "tmp" / "construct" / "lenses-report.md"
    ).read_text(encoding="utf-8")


def test_apply_seed_links(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cards = tmp_path / "01-Cards"
    _write_card(cards, "教学", ctype="domain", domains=["教学"])
    _write_card(cards, "空边主张")
    result = runner.invoke(
        construct_cmd, ["--root", str(tmp_path), "--apply-seed-links"]
    )
    assert result.exit_code == 0, result.output
    assert "Seed-links applied" in result.output
    text = (cards / "空边主张.md").read_text(encoding="utf-8")
    assert "applies-to" in text
    assert "教学" in text
    # 再跑应无新 writes
    result2 = runner.invoke(
        construct_cmd, ["--root", str(tmp_path), "--apply-seed-links"]
    )
    assert result2.exit_code == 0, result2.output
    assert "无 seed-links" in result2.output


def test_overload_threshold_uses_50_not_25(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cards = tmp_path / "01-Cards"
    _write_card(cards, "宏观经济学", ctype="domain", domains=["宏观经济学"])
    for i in range(49):
        _write_card(cards, f"主张{i}", domains=["宏观经济学"])
    store = Store(cards).load()
    assert not find_overloaded_domains(store)

    _write_card(cards, "主张49", domains=["宏观经济学"])
    _write_card(cards, "主张50", domains=["宏观经济学"])
    store = Store(cards).load()
    overloaded = find_overloaded_domains(store)
    assert any(d["id"] == "宏观经济学" for d in overloaded)


def test_suggest_domain_splits_from_member_titles(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cards = tmp_path / "01-Cards"
    _write_card(cards, "宏观经济学", ctype="domain", domains=["宏观经济学"])
    for i in range(55):
        _write_card(
            cards,
            f"货币{i}",
            title=f"货币政策工具{i}",
            domains=["宏观经济学"],
        )
    store = Store(cards).load()
    splits = suggest_domain_splits(store, top_n=3)
    assert any(op.get("term") == "货币政策" for op in splits)
    assert all(op["lens"] == "cluster" for op in splits)
    assert all(op["domain"] == "宏观经济学" for op in splits)


def test_cross_domain_signal_shared_instance(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cards = tmp_path / "01-Cards"
    _write_card(cards, "物理学", ctype="domain", domains=["物理学"])
    _write_card(cards, "经济学", ctype="domain", domains=["经济学"])
    _write_card(
        cards,
        "均衡概念",
        title="均衡概念",
        domains=["物理学", "经济学"],
    )
    store = Store(cards).load()
    signals = collect_structure_signals(store, [])
    cross = signals.get("cross_domain", [])
    assert any("物理学" in s and "经济学" in s for s in cross), cross
