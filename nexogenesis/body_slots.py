"""正文语义槽校验（按标题同义匹配）+ 单卡实质密度警告。"""

from __future__ import annotations

import re

HEADING_RE = re.compile(r"^#{1,3}\s+(.+?)\s*$", re.MULTILINE)
SECTION_RE = re.compile(
    r"^#{1,3}\s+(?P<title>.+?)\s*$",
    re.MULTILINE,
)

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

_CORE_ALIASES = {
    "claim": ["一句话主张", "核心表达", "主张"],
    "phenomenon": ["模式描述"],
    "model": ["核心思想", "核心表达"],
    "entity": ["定义"],
    "conflict": ["核心分歧点", "分歧点"],
    "domain": ["核心问题"],
    "method": ["步骤"],
}

_EVIDENCE_ALIASES = {
    "claim": ["依据", "依据与细节"],
    "phenomenon": ["典型实例", "实例"],
    "model": ["关键组件", "关键组件与关系", "结构关系", "因果链条"],
    "entity": ["关键属性"],
    "conflict": ["各自证据/代价", "各自证据", "证据与代价"],
    "domain": ["边界", "内在张力"],
    "method": ["输入", "输出"],
}

_HOLLOW_MARKS = (
    "原文未提及：具体依据",
    "原文未提及：摘录",
    "原文未提及：未讨论",
    "关联假设，证据待检验",
    "图表质料，宜并入",
    "证据不足",
    "待补充",
)


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
    if MISSING_MARK in (body or ""):
        return True
    return False


def validate_slots(body: str, slots: dict[str, list[str]]) -> list[str]:
    headings = extract_headings(body)
    errors: list[str] = []
    for slot_name, aliases in slots.items():
        if not _slot_satisfied(body, headings, aliases):
            errors.append(
                f"缺少语义槽「{slot_name}」（可用标题：{', '.join(aliases)}；或写「原文未提及」）"
            )
    return errors


def validate_card_body(card_type: str, body: str) -> list[str]:
    slots = CARD_SLOTS.get(card_type)
    if not slots:
        return [f"未知卡片类型：{card_type}"]
    return validate_slots(body, slots)


def validate_buffer_body(role: str, body: str) -> list[str]:
    """Buffer 闸门：快切片不强制四级标题槽；只拦空/近空正文。

    `MEANING_UNIT_SLOTS` / `ARTIFACT_SLOTS` 保留供文档与兼容；默认校验不再要求填槽。
    `--strict-body` 时把本函数错误升为 hard error（仍是空正文，不是缺标题）。
    """
    plain = _norm(body or "")
    if not plain:
        return ["Buffer 正文为空"]
    if len(plain) < 20:
        return ["Buffer 正文过短（意义切片应可读，非标题壳）"]
    # artifact 若几乎无内容且无表/图痕迹，仍提示（strict 时可挡）
    if role in ("artifact-table", "artifact-figure"):
        if len(plain) < 40 and "|" not in (body or "") and "图" not in (body or "") and "表" not in (body or ""):
            return ["artifact 正文过薄：应内嵌进 meaning-unit，或写出可独立阅读的转写与观察"]
    return []


def _section_text(body: str, aliases: list[str]) -> str:
    if not body:
        return ""
    matches = list(SECTION_RE.finditer(body))
    for i, m in enumerate(matches):
        if not _heading_matches(m.group("title"), aliases):
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        return body[start:end].strip()
    return ""


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip("　 \t\n\r「」\"'"))


def _almost_echo(a: str, b: str) -> bool:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
    if len(shorter) >= 8 and shorter in longer and len(longer) - len(shorter) <= 12:
        return True
    return False


def buffer_substance_warnings(
    *,
    role: str,
    title: str,
    body: str,
) -> list[str]:
    """Compile/Buffer 空心警告：快切片也须可读；形式过关 ≠ 可消化质料。"""
    warnings: list[str] = []
    body = body or ""
    title = title or ""
    plain = _norm(body)
    if 20 <= len(plain) < 48:
        warnings.append("切片偏薄：digest 读起来不舒服；宜并入相邻片或补机制/数字/短摘录")

    # 有旧式四级标题时仍检查空心填槽；自由正文则看开篇是否回声标题
    core = _section_text(body, ["核心表达", "一句话主张", "核心思想", "定义", "模式描述"])
    evid = _section_text(body, ["依据与细节", "依据", "细节", "关键组件"])
    quote = _section_text(body, ["原文摘录", "摘录", "原文"])
    if role == "meaning-unit":
        if core and _almost_echo(core, title):
            warnings.append("meaning-unit 核心几乎复读 title（薄片，digest 易变空心卡）")
        elif not core and title and _almost_echo(plain[: max(12, len(_norm(title)) + 8)], title):
            warnings.append("正文开篇几乎复读 title（薄片）；应写出机制或依据")
        if evid and (
            _norm(evid).startswith("原文未提及")
            or any(m in evid for m in _HOLLOW_MARKS)
        ):
            warnings.append("依据空洞：勿用「原文未提及」凑格式，应少切或并入他片")
        if quote and _norm(quote).startswith("原文未提及"):
            warnings.append("摘录槽空壳")
        if any(m in body for m in _HOLLOW_MARKS) and len(plain) < 120:
            warnings.append("正文含空心套话且过短：不适合作为消化原料")
        if re.search(r"或与|衔接|待检验", title) and (
            (evid and ("原文未提及" in evid or "待检验" in evid))
            or (not evid and ("待检验" in body or "衔接" in body))
        ):
            warnings.append("标题像 link-hypothesis：应改 role 或并入 tension/link，勿冒充 meaning-unit")
    if role in ("artifact-table", "artifact-figure"):
        if re.match(r"^(图|表)\s*\d*", title) and (
            "宜并入" in body or len(plain) < 40 or "关键观察" not in body
        ):
            if "宜并入" in body or len(plain) < 80:
                warnings.append(
                    "artifact 过薄或自承宜并入：compile 应默认内嵌进 meaning-unit，勿单开空心表/图块"
                )
    return warnings


def card_substance_warnings(
    *,
    card_id: str,
    title: str,
    card_type: str,
    body: str,
) -> list[str]:
    """
    单卡实质密度警告（不挡写入）：卡片应是可独立阅读的意义单元。
    槽位齐全但内容空洞时仍会报警。
    """
    warnings: list[str] = []
    body = body or ""
    core_aliases = _CORE_ALIASES.get(card_type) or []
    evid_aliases = _EVIDENCE_ALIASES.get(card_type) or []
    core = _section_text(body, core_aliases) if core_aliases else ""
    evid = _section_text(body, evid_aliases) if evid_aliases else ""
    quote = _section_text(body, ["原文摘录", "摘录", "原文"])

    if core and _almost_echo(core, title):
        warnings.append(
            f"{card_id}: 核心槽几乎复读标题——单卡无法独立解释问题；"
            "请写可复述的机制/判断，勿只回声标题"
        )
    if core and len(_norm(core)) < 12 and card_type in (
        "claim", "model", "conflict", "entity"
    ):
        warnings.append(f"{card_id}: 核心表达过短，单卡阅读信息不足")

    if evid:
        evid_norm = _norm(evid)
        if evid_norm.startswith("原文未提及") or any(m in evid for m in _HOLLOW_MARKS):
            warnings.append(
                f"{card_id}: 依据/细节槽空洞（仅「原文未提及」或待检验套话）——"
                "无实质则勿建卡，应 skip 或并入他卡"
            )
        elif len(evid_norm) < 16 and card_type in ("claim", "model", "phenomenon"):
            warnings.append(f"{card_id}: 依据/实例过薄，读完不知为何成立")

    if quote and (
        _norm(quote).startswith("原文未提及")
        or quote.strip() in ("原文未提及：摘录。", "原文未提及：摘录")
    ):
        warnings.append(
            f"{card_id}: 原文摘录槽为空壳；有来源时应留可核对短引"
        )

    if card_type == "phenomenon" and re.match(r"^(图|表)\s*\d*", title or ""):
        if not core or _almost_echo(core, title) or "宜并入" in body:
            warnings.append(
                f"{card_id}: 图表类 phenomenon 不宜作独立意义单元——"
                "应并入相关 model/claim 的依据槽，或写成带解读的机制说明"
            )

    if card_type == "claim" and re.search(r"或与|衔接|假设|待检验", title or ""):
        if not evid or "原文未提及" in evid or "待检验" in evid:
            warnings.append(
                f"{card_id}: 标题像 link-hypothesis，正文无实质——"
                "应作关系/问题清单，勿落成空心 claim"
            )

    return warnings
