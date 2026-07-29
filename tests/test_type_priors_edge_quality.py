from pathlib import Path

from nexogenesis.commands.init import init_cmd
from nexogenesis.graph.retrieve import pick_seeds
from nexogenesis.ingest.edge_quality import edge_quality_stats, edge_quality_warnings
from nexogenesis.store import Store
from nexogenesis.thinking.type_priors import (
    looks_like_chart_card,
    type_prior_score,
)
from click.testing import CliRunner


def _card(
    cards: Path,
    cid: str,
    *,
    ctype: str = "claim",
    title: str | None = None,
    relations: str = "[]",
    maturity: str = "seed",
) -> None:
    title = title or cid
    (cards / f"{cid}.md").write_text(
        "---\n"
        f"id: {cid}\n"
        f"title: {title}\n"
        f"type: {ctype}\n"
        f"maturity: {maturity}\nlifecycle: active\n"
        "domains: [教学]\norigin: document\nsources: []\n"
        f"relations: {relations}\n"
        "created: '2026-07-29'\nupdated: '2026-07-29'\n"
        "---\n\n## 正文\n\n　　测试。\n",
        encoding="utf-8",
    )


def test_type_prior_prefers_model_over_chart_phenomenon(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cards = tmp_path / "01-Cards"
    _card(cards, "教学", ctype="domain")
    _card(cards, "周期模型", ctype="model", title="康波与地产共振模型", maturity="growing")
    _card(cards, "图64指数", ctype="phenomenon", title="图64 房价指数表")
    store = Store(cards).load()
    model = store.cards["周期模型"]
    chart = store.cards["图64指数"]
    assert looks_like_chart_card(chart)
    assert type_prior_score(model, None) > type_prior_score(chart, None)

    seeds = pick_seeds(store, query="地产 共振 房价")
    # 同相关度下模型应排在图表 phenomenon 前或至少入选
    assert "周期模型" in seeds
    if "图64指数" in seeds:
        assert seeds.index("周期模型") < seeds.index("图64指数")


def test_edge_quality_detects_applies_to_overload(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    cards = tmp_path / "01-Cards"
    _card(cards, "教学", ctype="domain")
    for i in range(10):
        _card(
            cards,
            f"主张{i}",
            relations="[{target: 教学, type: applies-to, note: hang}]",
        )
    store = Store(cards).load()
    stats = edge_quality_stats(store)
    assert stats["applies_to_ratio"] >= 0.9
    assert stats["only_applies_to_count"] >= 8
    warns = edge_quality_warnings(store, min_instances=8)
    assert any("applies-to" in w for w in warns)
    assert any("语义边" in w for w in warns)
