from pathlib import Path

from nexogenesis.commands.init import init_cmd
from nexogenesis.ingest.structure_signals import collect_structure_signals
from nexogenesis.store import Store
from click.testing import CliRunner


def _write_card(cards: Path, cid: str, ctype: str, *, relations: str = "relations: []\n"):
    cards.joinpath(f"{cid}.md").write_text(
        f"---\nid: {cid}\ntitle: {cid}\ntype: {ctype}\nmaturity: seed\n"
        f"lifecycle: active\ndomains: [教学]\norigin: document\nsources: []\n"
        f"{relations}"
        f"created: '2026-07-28'\nupdated: '2026-07-28'\n---\n\n"
        f"## 核心\n\n　　关于 {cid}。\n",
        encoding="utf-8",
    )


def test_hollow_relations_summarized(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cards = tmp_path / "01-Cards"
    (cards / "教学.md").write_text(
        "---\nid: 教学\ntitle: 教学\ntype: domain\nmaturity: growing\n"
        "lifecycle: active\ndomains: [教学]\norigin: user\nsources: []\nrelations: []\n"
        "created: '2026-07-28'\nupdated: '2026-07-28'\n---\n\n"
        "## 核心问题\n\n　　教学。\n\n## 边界\n\n　　测。\n\n## 内在张力\n\n　　测。\n",
        encoding="utf-8",
    )
    for i in range(3):
        _write_card(cards, f"主张{i}", "claim")
    _write_card(
        cards,
        "冲突甲",
        "conflict",
        relations=(
            "relations:\n"
            "  - target: 教学\n"
            "    type: applies-to\n"
            "    note: 仅挂领域\n"
        ),
    )
    store = Store(cards).load()
    signals = collect_structure_signals(store, [])
    cluster = " ".join(signals["cluster"])
    assert "链接空洞" in cluster
    assert "优先补语义边" in cluster or "语义边" in cluster
    distinguish = " ".join(signals["distinguish"])
    assert "缺少 involves" in distinguish
    assert "不要只写 applies-to" in distinguish or "involves" in distinguish


def test_doctor_warns_sparse_graph(tmp_path: Path):
    from nexogenesis.commands.doctor import doctor_cmd

    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cards = tmp_path / "01-Cards"
    (cards / "教学.md").write_text(
        "---\nid: 教学\ntitle: 教学\ntype: domain\nmaturity: growing\n"
        "lifecycle: active\ndomains: [教学]\norigin: user\nsources: []\nrelations: []\n"
        "created: '2026-07-28'\nupdated: '2026-07-28'\n---\n\n"
        "## 核心问题\n\n　　教学。\n\n## 边界\n\n　　测。\n\n## 内在张力\n\n　　测。\n\n"
        "## 原文摘录\n\n> 教学\n",
        encoding="utf-8",
    )
    for i in range(5):
        _write_card(cards, f"主张{i}", "claim")
    # 补 claim 最小槽，避免 semantic 槽变成 ISSUE 干扰断言
    for i in range(5):
        p = cards / f"主张{i}.md"
        p.write_text(
            f"---\nid: 主张{i}\ntitle: 主张{i}\ntype: claim\nmaturity: seed\n"
            f"lifecycle: active\ndomains: [教学]\norigin: document\nsources: []\n"
            f"relations: []\ncreated: '2026-07-28'\nupdated: '2026-07-28'\n---\n\n"
            f"## 一句话主张\n\n　　主张{i}。\n\n## 依据\n\n　　测。\n\n"
            f"## 已知限制\n\n　　原文未提及：限制。\n\n## 原文摘录\n\n> x\n",
            encoding="utf-8",
        )
    result = runner.invoke(doctor_cmd, ["--root", str(tmp_path)])
    assert "图谱偏稀" in result.output
    assert result.exit_code == 0, result.output