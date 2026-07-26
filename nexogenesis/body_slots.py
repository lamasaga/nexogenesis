"""正文语义槽校验（按标题同义匹配）。"""

from __future__ import annotations

import re

HEADING_RE = re.compile(r"^#{1,3}\s+(.+?)\s*$", re.MULTILINE)

MISSING_MARK = "原文未提及"

# role / type → list of slot groups; each group is a list of acceptable heading names
MEANING_UNIT_SLOTS = {
    "核心表达": ["核心表达", "一句话主张", "核心思想", "核心问题", "定义", "模式描述"],
    "依据与细节": ["依据与细节", "依据", "细节", "关键组件", "关键组件与关系", "步骤", "关键属性"],
    "限制与边界": [
        "限制与边界", "已知限制", "失效边界", "适用边界", "边界",
        "反例与失效条件", "调和可能", "边界与局限",
    ],
    "原文摘录": ["原文摘录", "摘录", "原文"],
}

ARTIFACT_SLOTS = {
    "标题与编号": ["标题与编号", "标题", "编号"],
    "内容转写": ["内容转写", "表格内容", "图示描述", "内容"],
}

CARD_SLOTS: dict[str, dict[str, list[str]]] = {
    "domain": {
        "核心问题": ["核心问题"],
        "边界": ["边界"],
        "内在张力": ["内在张力"],
        "原文摘录": ["原文摘录", "摘录", "原文"],
    },
    "claim": {
        "一句话主张": ["一句话主张", "核心表达", "主张"],
        "依据": ["依据", "依据与细节"],
        "已知限制": ["已知限制", "限制与边界", "限制"],
        "原文摘录": ["原文摘录", "摘录", "原文"],
    },
    "phenomenon": {
        "模式描述": ["模式描述"],
        "典型实例": ["典型实例", "实例"],
        "反例与失效条件": ["反例与失效条件", "反例", "失效条件"],
        "原文摘录": ["原文摘录", "摘录", "原文"],
    },
    "model": {
        "核心思想": ["核心思想", "核心表达"],
        "关键组件": ["关键组件", "关键组件与关系"],
        "结构关系": ["结构关系", "因果链条", "结构 / 因果", "结构", "因果"],
        "失效边界": ["失效边界", "限制与边界"],
        "原文摘录": ["原文摘录", "摘录", "原文"],
    },
    "method": {
        "输入": ["输入"],
        "步骤": ["步骤"],
        "输出": ["输出"],
        "适用边界": ["适用边界", "限制与边界"],
        "原文摘录": ["原文摘录", "摘录", "原文"],
    },
    "entity": {
        "定义": ["定义"],
        "关键属性": ["关键属性"],
        "边界与局限": ["边界与局限", "边界", "局限"],
        "来源": ["来源"],
        "原文摘录": ["原文摘录", "摘录", "原文"],
    },
    "conflict": {
        "对立双方": ["对立双方"],
        "核心分歧点": ["核心分歧点", "分歧点"],
        "各自证据": ["各自证据/代价", "各自证据", "各自证据 / 代价", "证据与代价"],
        "调和可能": ["调和可能"],
        "原文摘录": ["原文摘录", "摘录", "原文"],
    },
}


def extract_headings(body: str) -> list[str]:
    return [m.group(1).strip() for m in HEADING_RE.finditer(body or "")]


def _heading_matches(heading: str, aliases: list[str]) -> bool:
    h = heading.strip()
    for alias in aliases:
        if h == alias or alias in h or h in alias:
            return True
    return False


def _slot_satisfied(body: str, headings: list[str], aliases: list[str]) -> bool:
    if any(_heading_matches(h, aliases) for h in headings):
        return True
    # 允许整篇用「原文未提及」显式覆盖缺槽（宽松：正文出现即过）
    if MISSING_MARK in (body or ""):
        return True
    return False


def validate_slots(body: str, slots: dict[str, list[str]]) -> list[str]:
    headings = extract_headings(body)
    errors: list[str] = []
    for slot_name, aliases in slots.items():
        if not _slot_satisfied(body, headings, aliases):
            errors.append(f"缺少语义槽「{slot_name}」（可用标题：{', '.join(aliases)}；或写「原文未提及」）")
    return errors


def validate_card_body(card_type: str, body: str) -> list[str]:
    slots = CARD_SLOTS.get(card_type)
    if not slots:
        return [f"未知卡片类型：{card_type}"]
    return validate_slots(body, slots)


def validate_buffer_body(role: str, body: str) -> list[str]:
    if role == "meaning-unit":
        return validate_slots(body, MEANING_UNIT_SLOTS)
    if role in ("artifact-table", "artifact-figure"):
        # 来源在 frontmatter；正文至少有内容转写类信息或标题节
        errs = validate_slots(body, ARTIFACT_SLOTS)
        # 若正文足够长且含表格/描述，可放宽标题节
        if errs and len(body or "") >= 40 and ("|" in body or "图" in body or "表" in body):
            return []
        return errs
    # 其他 role：暂不强制正文骨架
    return []
