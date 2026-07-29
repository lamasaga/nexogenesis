"""边质量与类型结构诊断（语义边 vs applies-to 挂靠）。"""

from __future__ import annotations

from typing import Any

from nexogenesis.models import CardType, RelationType
from nexogenesis.store import Store

# 思想连通边（相对「只挂领域」）
SEMANTIC_TYPES = {
    RelationType.BASED_ON,
    RelationType.SUPPORTS,
    RelationType.CONFLICTS_WITH,
    RelationType.INVOLVES,
    RelationType.EXTENDS,
    RelationType.INFLUENCES,
    RelationType.EXAMPLE_OF,
}


def edge_quality_stats(store: Store) -> dict[str, Any]:
    instances = [c for c in store.cards.values() if c.type != CardType.DOMAIN]
    total_out = 0
    applies = 0
    semantic = 0
    hollow = 0
    only_applies = 0
    for c in instances:
        if not c.relations:
            hollow += 1
            continue
        types = {r.type for r in c.relations}
        total_out += len(c.relations)
        applies += sum(1 for r in c.relations if r.type == RelationType.APPLIES_TO)
        semantic += sum(1 for r in c.relations if r.type in SEMANTIC_TYPES)
        if types <= {RelationType.APPLIES_TO}:
            only_applies += 1

    n = len(instances) or 1
    by_type = {
        t.value: sum(1 for c in store.cards.values() if c.type == t)
        for t in CardType
    }
    seed_n = sum(1 for c in store.cards.values() if c.maturity.value == "seed")
    return {
        "instance_count": len(instances),
        "hollow_count": hollow,
        "only_applies_to_count": only_applies,
        "outgoing_total": total_out,
        "applies_to_count": applies,
        "semantic_count": semantic,
        "applies_to_ratio": (applies / total_out) if total_out else 0.0,
        "only_applies_ratio": only_applies / n,
        "by_type": by_type,
        "seed_count": seed_n,
        "card_count": len(store.cards),
        "seed_ratio": seed_n / len(store.cards) if store.cards else 0.0,
        "model_count": by_type.get("model", 0),
        "entity_count": by_type.get("entity", 0),
        "claim_count": by_type.get("claim", 0),
    }


def edge_quality_warnings(store: Store, *, min_instances: int = 8) -> list[str]:
    stats = edge_quality_stats(store)
    if stats["instance_count"] < min_instances:
        return []
    warnings: list[str] = []
    if stats["applies_to_ratio"] >= 0.45 and stats["outgoing_total"] >= 20:
        warnings.append(
            f"applies-to 过载：出边中 {stats['applies_to_ratio']:.0%} 为 applies-to "
            f"（{stats['applies_to_count']}/{stats['outgoing_total']}）。"
            "边数≠思想连通；优先补 based-on/supports/conflicts-with/involves，"
            "勿再无脑 seed-link 挂 domain。"
        )
    if stats["only_applies_ratio"] >= 0.35:
        warnings.append(
            f"语义边不足：{stats['only_applies_to_count']}/{stats['instance_count']} "
            "张非 domain 卡出边仅有 applies-to（或等价挂靠）。"
            "construct --lens articulate 应抽时间线/工具箱 entity 与机制 model。"
        )
    models = stats["model_count"]
    entities = stats["entity_count"]
    claims = stats["claim_count"]
    if claims >= 30 and models + entities < max(3, claims // 40):
        warnings.append(
            f"主张过碎、枢纽过少：claim={claims} 而 model+entity={models + entities}。"
            "优先升格/新建时间—政策—变量枢纽，少再拆近义 claim。"
        )
    if stats["card_count"] >= 40 and stats["seed_ratio"] >= 0.9:
        warnings.append(
            f"maturity 几乎全为 seed（{stats['seed_count']}/{stats['card_count']}）。"
            "跨报告复现或对话高频引用的卡可晋升 growing；"
            "origin:system 升 mature/theory active 仍须用户批准。"
        )
    return warnings


def edge_quality_signals(store: Store) -> dict[str, list[str]]:
    """供 construct 镜头合并的信号。"""
    out: dict[str, list[str]] = {
        "cluster": [],
        "distinguish": [],
        "articulate": [],
        "cross_source": [],
    }
    for w in edge_quality_warnings(store, min_instances=5):
        if "applies-to" in w or "语义边" in w or "枢纽过少" in w:
            out["articulate"].append(w)
            out["cluster"].append(w)
        elif "seed" in w or "maturity" in w:
            out["articulate"].append(w)
        else:
            out["articulate"].append(w)
    stats = edge_quality_stats(store)
    # 图表类 phenomenon 过多提示
    chartish = [
        cid
        for cid, c in store.cards.items()
        if c.type == CardType.PHENOMENON
        and any(k in f"{cid}{c.title}" for k in ("图", "表", "索引", "figure", "table"))
    ]
    if len(chartish) >= 8:
        show = ", ".join(f"`{x}`" for x in chartish[:5])
        out["articulate"].append(
            f"图表/索引类 phenomenon 较多（≥{len(chartish)}，如 {show}…）："
            "宜并入相关 model 的依据槽；retrieve 已对其降权，建构勿再堆独立图注卡。"
        )
    if stats["model_count"] + stats["entity_count"] < 3 and stats["claim_count"] >= 15:
        out["articulate"].append(
            "建议先立时间线/政策工具箱/关键变量 entity 或机制 model，再挂 claim——"
            "事实序列默认外查，不进库膨胀。"
        )
    return out
