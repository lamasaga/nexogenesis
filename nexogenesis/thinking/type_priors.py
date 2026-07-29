"""答题骨架偏置：优先 model/conflict/entity，压低图表类 phenomenon。"""

from __future__ import annotations

import re
from typing import Any

from nexogenesis.models import Card, CardType

# 标题/id 像「图注、表、索引」时额外降权（结构召回 ≠ 答题骨架）
_CHART_HINT_RE = re.compile(
    r"(图\s*\d+|表\s*\d+|图注|附图|插图|索引表|目录表|figure|table|chart|附录表)",
    re.IGNORECASE,
)

DEFAULT_TYPE_PRIORS: dict[str, Any] = {
    "enabled": True,
    "by_type": {
        "model": 0.45,
        "conflict": 0.40,
        "entity": 0.35,
        "method": 0.25,
        "claim": 0.10,
        "phenomenon": -0.05,
        "domain": 0.05,
    },
    "chart_phenomenon_penalty": -0.40,
    "maturity_bonus": {
        "seed": 0.0,
        "growing": 0.15,
        "mature": 0.25,
    },
}


def looks_like_chart_card(card: Card) -> bool:
    hay = f"{card.id} {card.title}"
    return bool(_CHART_HINT_RE.search(hay))


def type_prior_score(card: Card, priors: dict[str, Any] | None) -> float:
    """加到 expansion / seed 相关分上的偏置（可正可负）。"""
    cfg = {**DEFAULT_TYPE_PRIORS, **(priors or {})}
    if not cfg.get("enabled", True):
        return 0.0
    by_type = {**(DEFAULT_TYPE_PRIORS["by_type"]), **(cfg.get("by_type") or {})}
    score = float(by_type.get(card.type.value, 0.0))
    if card.type == CardType.PHENOMENON and looks_like_chart_card(card):
        score += float(cfg.get("chart_phenomenon_penalty", -0.40))
    mat = (cfg.get("maturity_bonus") or {}).get(
        card.maturity.value if card.maturity else "seed", 0.0
    )
    score += float(mat or 0.0)
    return score


def type_prior_seed_boost(card: Card, priors: dict[str, Any] | None) -> int:
    """pick_seeds 用的整数加分（约 0–4）。"""
    s = type_prior_score(card, priors)
    if s >= 0.35:
        return 3
    if s >= 0.15:
        return 2
    if s >= 0.05:
        return 1
    if s <= -0.35:
        return -3
    if s < 0:
        return -1
    return 0
