from pathlib import Path

from nexogenesis.commands.init import init_cmd
from nexogenesis.graph.analyze import analyze_graph
from nexogenesis.graph.build import load_snapshot, rebuild_graph
from nexogenesis.graph.retrieve import graph_retrieve
from nexogenesis.rag.index import index_rag, rag_stats
from nexogenesis.rag.search import rag_search
from nexogenesis.retrieve.context_package import build_context_package
from click.testing import CliRunner


def _card(cards_dir: Path, cid: str, *, domains: list[str], relations: list | None = None):
    rel_yaml = ""
    if relations:
        lines = ["relations:"]
        for r in relations:
            lines.append(f"  - target: {r['target']}")
            lines.append(f"    type: {r['type']}")
            lines.append(f'    note: "{r.get("note", "")}"')
        rel_yaml = "\n".join(lines) + "\n"
    else:
        rel_yaml = "relations: []\n"
    dom = ", ".join(domains)
    cards_dir.joinpath(f"{cid}.md").write_text(
        f"---\nid: {cid}\ntitle: {cid}\ntype: claim\nmaturity: seed\n"
        f"lifecycle: active\ndomains: [{dom}]\norigin: document\nsources: []\n"
        f"{rel_yaml}"
        f"created: '2026-07-24'\nupdated: '2026-07-24'\n---\n\n"
        f"## 一句话主张\n\n　　关于 {cid}。\n",
        encoding="utf-8",
    )


def test_graph_rebuild_empty(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    snap = rebuild_graph(tmp_path)
    assert snap.node_count == 0
    assert snap.edge_count == 0
    assert load_snapshot(tmp_path) is not None


def test_graph_retrieve_with_relations(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cards = tmp_path / "01-Cards"
    (cards / "教学.md").write_text(
        "---\nid: 教学\ntitle: 教学\ntype: domain\nmaturity: growing\n"
        "lifecycle: active\ndomains: [教学]\norigin: user\nsources: []\nrelations: []\n"
        "created: '2026-07-24'\nupdated: '2026-07-24'\n---\n\n## 核心问题\n\n　　教学。\n",
        encoding="utf-8",
    )
    _card(cards, "反馈差距", domains=["教学"], relations=[{"target": "教学", "type": "applies-to"}])
    rebuild_graph(tmp_path)
    result = graph_retrieve(tmp_path, query="反馈", seeds=["教学"])
    assert result["status"] == "ok"
    ids = {n["id"] for n in result["nodes"]}
    assert "反馈差距" in ids or "教学" in ids


def test_graph_analyze_orphan(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    _card(tmp_path / "01-Cards", "孤立卡", domains=["教学"])
    (tmp_path / "01-Cards" / "教学.md").write_text(
        "---\nid: 教学\ntitle: 教学\ntype: domain\nmaturity: growing\n"
        "lifecycle: active\ndomains: [教学]\norigin: user\nsources: []\nrelations: []\n"
        "created: '2026-07-24'\nupdated: '2026-07-24'\n---\n\n## 核心问题\n\n　　x\n",
        encoding="utf-8",
    )
    metrics = analyze_graph(tmp_path, rebuild=True)
    assert metrics["orphan_count"] >= 1
    assert (tmp_path / ".nexogenesis/graph/reports/latest-summary.md").exists()


def test_rag_index_buffer_and_search(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    buf = tmp_path / "05-Buffer" / "meaning-unit"
    buf.mkdir(parents=True, exist_ok=True)
    (buf / "2026-07-24-a.md").write_text(
        "---\ntitle: DDPM 扩散模型\nrole: meaning-unit\nsource: paper\n"
        "status: scratch\ncreated: '2026-07-24'\nupdated: '2026-07-24'\n---\n\n"
        "## 核心表达\n\n　　扩散模型通过逐步去噪生成样本。\n",
        encoding="utf-8",
    )
    stats = index_rag(tmp_path, kinds=["buffer"])
    assert stats["chunk_count"] >= 1
    hits = rag_search(tmp_path, "扩散模型")
    assert len(hits) >= 1
    assert hits[0]["kind"] == "buffer"


def test_rag_discussion_nascent(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    disc = tmp_path / "04-OutBox" / "discussions"
    disc.mkdir(parents=True, exist_ok=True)
    (disc / "2026-07-27-test.md").write_text(
        "---\ntitle: 研讨\ntype: discussion\norigin: user\nlinked_cards: []\n"
        "created: '2026-07-27'\nupdated: '2026-07-27'\n---\n\n"
        "## 议题\n\n　　有效反思与自我感动的边界。\n",
        encoding="utf-8",
    )
    index_rag(tmp_path, kinds=["discussion"])
    hits = rag_search(tmp_path, "自我感动", kinds=["discussion"])
    assert hits and hits[0]["attribution"] == "nascent"


def test_unified_retrieve(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cards = tmp_path / "01-Cards"
    (cards / "教学.md").write_text(
        "---\nid: 教学\ntitle: 教学\ntype: domain\nmaturity: growing\n"
        "lifecycle: active\ndomains: [教学]\norigin: user\nsources: []\nrelations: []\n"
        "created: '2026-07-24'\nupdated: '2026-07-24'\n---\n\n## 核心问题\n\n　　教学。\n",
        encoding="utf-8",
    )
    rebuild_graph(tmp_path)
    index_rag(tmp_path, kinds=["card_excerpt"])
    pkg = build_context_package(tmp_path, query="教学", mode="talk")
    assert pkg["structure"]["nodes"]
    assert pkg["mode"] == "talk"


def test_retrieve_cli(tmp_path: Path):
    from nexogenesis.commands.retrieve import retrieve_cmd

    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    result = runner.invoke(retrieve_cmd, ["--root", str(tmp_path), "--query", "test"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".nexogenesis" / "tmp" / "retrieve" / "context.yaml").exists()


def test_graph_export_graphml(tmp_path: Path):
    from nexogenesis.commands.graph import graph_cmd

    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cards = tmp_path / "01-Cards"
    (cards / "教学.md").write_text(
        "---\nid: 教学\ntitle: 教学\ntype: domain\nmaturity: growing\n"
        "lifecycle: active\ndomains: [教学]\norigin: user\nsources: []\nrelations: []\n"
        "created: '2026-07-24'\nupdated: '2026-07-24'\n---\n\n## 核心问题\n\n　　教学。\n",
        encoding="utf-8",
    )
    _card(cards, "反馈差距", domains=["教学"], relations=[{"target": "教学", "type": "applies-to"}])
    result = runner.invoke(
        graph_cmd,
        ["export", "--root", str(tmp_path), "--center", "教学", "--hops", "1"],
    )
    assert result.exit_code == 0, result.output
    out = tmp_path / ".nexogenesis" / "tmp" / "graph" / "graph.graphml"
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "<graphml" in text
    assert "node id=" in text


def test_rag_incremental_reindex(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    buf = tmp_path / "05-Buffer" / "meaning-unit"
    buf.mkdir(parents=True, exist_ok=True)
    p = buf / "2026-07-24-a.md"
    p.write_text(
        "---\ntitle: 初版\nrole: meaning-unit\nsource: paper\n"
        "status: scratch\ncreated: '2026-07-24'\nupdated: '2026-07-24'\n---\n\n"
        "## 核心表达\n\n　　扩散模型初版。\n",
        encoding="utf-8",
    )
    index_rag(tmp_path, kinds=["buffer"], incremental=True)
    assert rag_search(tmp_path, "初版")

    p.write_text(
        "---\ntitle: 修订\nrole: meaning-unit\nsource: paper\n"
        "status: scratch\ncreated: '2026-07-24'\nupdated: '2026-07-25'\n---\n\n"
        "## 核心表达\n\n　　扩散模型修订版内容。\n",
        encoding="utf-8",
    )
    index_rag(tmp_path, kinds=["buffer"], incremental=True)
    hits = rag_search(tmp_path, "修订版")
    assert hits and "修订版" in hits[0]["excerpt"]


def test_doctor_index_staleness_warning(tmp_path: Path):
    from nexogenesis.commands.doctor import doctor_cmd

    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cards = tmp_path / "01-Cards"
    (cards / "教学.md").write_text(
        "---\nid: 教学\ntitle: 教学\ntype: domain\nmaturity: growing\n"
        "lifecycle: active\ndomains: [教学]\norigin: user\nsources: []\nrelations: []\n"
        "created: '2026-07-24'\nupdated: '2026-07-24'\n---\n\n## 核心问题\n\n　　教学。\n",
        encoding="utf-8",
    )
    result = runner.invoke(doctor_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "graph" in result.output.lower() or "WARNING" in result.output


def test_construct_diagnose_includes_graph_analyze(tmp_path: Path):
    from nexogenesis.commands.construct import construct_cmd

    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    _card(tmp_path / "01-Cards", "孤立卡", domains=["教学"])
    (tmp_path / "01-Cards" / "教学.md").write_text(
        "---\nid: 教学\ntitle: 教学\ntype: domain\nmaturity: growing\n"
        "lifecycle: active\ndomains: [教学]\norigin: user\nsources: []\nrelations: []\n"
        "created: '2026-07-24'\nupdated: '2026-07-24'\n---\n\n## 核心问题\n\n　　x\n",
        encoding="utf-8",
    )
    result = runner.invoke(construct_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    report = (tmp_path / ".nexogenesis" / "tmp" / "construct" / "lenses-report.md").read_text(
        encoding="utf-8"
    )
    assert "图分析" in report or "graph analyze" in report.lower()
    assert (tmp_path / ".nexogenesis" / "tmp" / "construct" / "structure-ops-draft.md").exists()
