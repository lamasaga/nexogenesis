"""强信号：何时轻问用户（门铃层，不自动写入）。"""

from __future__ import annotations

import re
from typing import Any

from nexogenesis.thinking.config import get_nested

CAPTURE_PHRASES = re.compile(
    r"(记一下|记下|记下来|入库|capture|保存这条|留下这条)",
    re.IGNORECASE,
)
TENSION_PHRASES = re.compile(
    r"(但是|反过来|对立|矛盾|冲突|两难|一边.*一边|既要.*又要)"
)
INBOX_PHRASES = re.compile(
    r"(00-Inbox|Inbox|收件箱|未消化|那篇(文章|论文|材料)|放进.?编译|compile)",
    re.IGNORECASE,
)
HIGH_RISK = re.compile(
    r"(决策|要不要做|风险|跨域|因果|到底选哪个|慎重|判断一下)"
)
DISABLE_CAPTURE = re.compile(r"(先别记|别记了|不要捕获|别捕获|先聊别记)")


def evaluate_strong_signals(
    user_text: str,
    *,
    stm_slots: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
    card_ids_in_library: set[str] | None = None,
) -> list[dict[str, str]]:
    """
    返回信号列表：[{type, prompt, reason}, ...]
    捕获类提问仍须用户确认后才能 write。
    """
    cfg = config or {}
    ss = cfg.get("strong_signals") or {}
    if not ss.get("enabled", True):
        return []

    ask_on = ss.get("ask_on") or {}
    slots = stm_slots or {}
    turn = int(slots.get("turn") or 0)
    text = (user_text or "").strip()
    if not text:
        return []

    # 用户禁令
    if ss.get("honor_user_directives", True):
        if slots.get("signals_disabled_capture"):
            # 仍允许显式「记一下」
            pass
        if DISABLE_CAPTURE.search(text):
            return [{
                "type": "directive_ack",
                "prompt": "好的，本会话先不主动提捕获；你说「记一下」时再问。",
                "reason": "user_directive",
            }]

    signals: list[dict[str, str]] = []

    # 冷却（非显式捕获）
    cooldown = int(ss.get("cooldown_turns", 6))
    last = int(slots.get("last_signal_turn") or -999)
    in_cooldown = (turn - last) < cooldown and last >= 0

    max_cap = int(ss.get("max_capture_prompts_per_session", 2))
    cap_count = int(slots.get("capture_prompts") or 0)

    if ask_on.get("explicit_capture_phrase", True) and CAPTURE_PHRASES.search(text):
        signals.append({
            "type": "capture",
            "prompt": "要把刚才值得留下的整理成候选吗？（确认后才写入）",
            "reason": "explicit_capture_phrase",
        })
        return signals  # 显式捕获立即返回，不受冷却/上限（上限只限制主动）

    disabled = bool(slots.get("signals_disabled_capture")) and ss.get(
        "honor_user_directives", True
    )
    if disabled or in_cooldown:
        # 仍可建议摄入 / 加深（非捕获）
        pass

    def can_ask_capture() -> bool:
        if disabled:
            return False
        if in_cooldown:
            return False
        return cap_count < max_cap

    if (
        ask_on.get("clear_tension", True)
        and TENSION_PHRASES.search(text)
        and can_ask_capture()
    ):
        signals.append({
            "type": "conflict_draft",
            "prompt": "这里好像有对立，要不要立一张冲突草稿候选？（确认后才写入）",
            "reason": "clear_tension",
        })

    if ask_on.get("inbox_mention", True) and INBOX_PHRASES.search(text):
        signals.append({
            "type": "suggest_compile",
            "prompt": "要不要把提到的材料放进 compile 流程？",
            "reason": "inbox_mention",
        })

    if ask_on.get("high_risk_topic", True) and HIGH_RISK.search(text):
        signals.append({
            "type": "deepen_judge",
            "prompt": "这题偏决策/争议，要不要在对话里加深判一下？（默认不落盘）",
            "reason": "high_risk_topic",
        })

    if ask_on.get("repeated_question_in_stm", True):
        focus = (slots.get("focus") or "").strip()
        tensions = slots.get("tensions") or []
        if focus and len(focus) >= 4 and focus in text:
            # 粗：焦点再次出现
            signals.append({
                "type": "profile_question",
                "prompt": "这个问题反复出现，要不要写进问题清单？（确认后才写入）",
                "reason": "repeated_question_in_stm",
            })
        elif any(isinstance(t, str) and len(t) >= 4 and t in text for t in tensions):
            signals.append({
                "type": "profile_question",
                "prompt": "这条张力又出现了，要不要记进问题清单？",
                "reason": "repeated_question_in_stm",
            })

    if (
        ask_on.get("reusable_new_claim", True)
        and can_ask_capture()
        and _looks_like_claim(text)
    ):
        # 若库中已有完全同 id 则跳过（粗检）
        if card_ids_in_library and text[:20] in card_ids_in_library:
            pass
        else:
            signals.append({
                "type": "capture",
                "prompt": "这句话很像可复用主张，要不要留下候选？（确认后才写入）",
                "reason": "reusable_new_claim",
            })

    # 每轮最多 1 条主动捕获类 + 可附带非捕获
    capture_like = {"capture", "conflict_draft", "profile_question"}
    out: list[dict[str, str]] = []
    seen_types: set[str] = set()
    capture_emitted = False
    for s in signals:
        if s["type"] in seen_types:
            continue
        if s["type"] in capture_like:
            if capture_emitted or not can_ask_capture():
                if s["type"] != "capture" or capture_emitted:
                    if s["reason"] != "explicit_capture_phrase":
                        continue
            capture_emitted = True
        seen_types.add(s["type"])
        out.append(s)
        if len(out) >= 2:
            break
    return out


def _looks_like_claim(text: str) -> bool:
    if len(text) < 12 or len(text) > 200:
        return False
    if text.endswith("？") or text.endswith("?"):
        return False
    markers = ("应该", "必须", "本质是", "关键在于", "我认为", "其实是", "优先")
    return any(m in text for m in markers)
