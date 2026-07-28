"""注意力 YAML：加载、深合并、校验、解析有效配置。"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

KNOWN_PROFILES = ("talk", "answer", "judge", "digest", "construct")


def _scheme_default_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "schemes" / "default" / "attention.yaml"


def deep_merge(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    """递归合并；override 覆盖 base；list 整段替换。"""
    out = deepcopy(base) if base else {}
    if not override:
        return out
    for key, val in override.items():
        if (
            key in out
            and isinstance(out[key], dict)
            and isinstance(val, dict)
        ):
            out[key] = deep_merge(out[key], val)
        else:
            out[key] = deepcopy(val)
    return out


def _load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"attention 配置必须是 mapping: {path}")
    return data


def load_attention_config(root: Path) -> dict[str, Any]:
    """scheme 默认 ← 项目 schemes/default ← .nexogenesis/attention.yaml。"""
    root = root.resolve()
    layers: list[dict[str, Any]] = []

    bundled = _scheme_default_path()
    if bundled.exists():
        layers.append(_load_yaml_file(bundled))

    project_scheme = root / "schemes" / "default" / "attention.yaml"
    if project_scheme.exists() and project_scheme.resolve() != bundled.resolve():
        layers.append(_load_yaml_file(project_scheme))

    project_override = root / ".nexogenesis" / "attention.yaml"
    if project_override.exists():
        layers.append(_load_yaml_file(project_override))

    merged: dict[str, Any] = {}
    for layer in layers:
        merged = deep_merge(merged, layer)

    if not merged:
        merged = _builtin_fallback()
    return merged


def _builtin_fallback() -> dict[str, Any]:
    return {
        "version": 1,
        "active_profile": "talk",
        "stm": {
            "max_sessions": 10,
            "overflow": "drop",
            "update": "every_turn",
            "every_n_turns": 2,
            "path": ".nexogenesis/memory/stm",
        },
        "budget": {
            "chars": 16000,
            "card_slots": 12,
            "rag_chunks": 6,
            "recent_turns_in_prompt": 4,
        },
        "slots": {"core": 3, "expansion": 6, "conflict": 2},
        "weights": {
            "expansion": {
                "relevance": 0.55,
                "novelty": 0.35,
                "already_cited_penalty": 0.40,
            },
            "conflict": {
                "relevance": 0.40,
                "tension_match": 0.35,
                "conflicts_edge": 0.25,
            },
        },
        "graph": {
            "hops": 2,
            "prefer_bridge_nodes": True,
            "expansion_prefer_weak_ties": True,
        },
        "rag": {"enabled": True, "max_chunks": 6, "mark_nascent": True},
        "profiles": {},
        "strong_signals": {
            "enabled": True,
            "max_capture_prompts_per_session": 2,
            "cooldown_turns": 6,
            "ask_on": {
                "explicit_capture_phrase": True,
                "reusable_new_claim": True,
                "clear_tension": True,
                "repeated_question_in_stm": True,
                "high_risk_topic": True,
                "inbox_mention": True,
            },
            "honor_user_directives": True,
        },
        "session_overrides": {},
    }


def validate_attention_config(cfg: dict[str, Any]) -> tuple[list[str], list[str]]:
    """返回 (errors, warnings)。"""
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(cfg, dict):
        return ["attention 配置不是 mapping"], []

    version = cfg.get("version", 1)
    if version != 1:
        warnings.append(f"未知 attention.version={version}，按 v1 解释")

    stm = cfg.get("stm") or {}
    max_s = stm.get("max_sessions", 10)
    if not isinstance(max_s, int) or max_s < 1 or max_s > 50:
        errors.append("stm.max_sessions 须为 1–50 的整数")

    overflow = stm.get("overflow", "drop")
    if overflow not in ("drop", "fossil"):
        errors.append("stm.overflow 须为 drop 或 fossil")

    slots = cfg.get("slots") or {}
    for key in ("core", "expansion", "conflict"):
        v = slots.get(key, 0)
        if not isinstance(v, int) or v < 0:
            errors.append(f"slots.{key} 须为非负整数")

    budget = cfg.get("budget") or {}
    for key in ("chars", "card_slots", "rag_chunks"):
        v = budget.get(key)
        if v is not None and (not isinstance(v, int) or v < 0):
            errors.append(f"budget.{key} 须为非负整数")

    profile = cfg.get("active_profile", "talk")
    if profile not in KNOWN_PROFILES and profile not in (cfg.get("profiles") or {}):
        warnings.append(f"active_profile={profile} 无对应 profiles 块，将用全局默认")

    return errors, warnings


def resolve_effective_config(
    cfg: dict[str, Any],
    *,
    profile: str | None = None,
    session_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """合并 active_profile / 指定 profile / session_overrides / 文件内 session_overrides。"""
    base = deepcopy(cfg)
    name = profile or base.get("active_profile") or "talk"
    profiles = base.get("profiles") or {}
    profile_patch = profiles.get(name) or {}
    effective = deep_merge(base, profile_patch)

    file_overrides = base.get("session_overrides") or {}
    if file_overrides:
        effective = deep_merge(effective, file_overrides)
    if session_overrides:
        effective = deep_merge(effective, session_overrides)

    effective["resolved_profile"] = name
    return effective


def get_nested(cfg: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = cfg
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur
