"""Prompt 模板加载与渲染。"""

from pathlib import Path

from jinja2 import Template

from nexogenesis.ingest import VALID_BUFFER_ROLES


DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "schemes" / "default" / "prompts"


def _load_template(name: str, scheme_dir: Path | None = None) -> Template:
    dirs = []
    if scheme_dir:
        dirs.append(scheme_dir / "prompts")
    dirs.append(DEFAULT_PROMPTS_DIR)
    for d in dirs:
        path = d / f"{name}.txt"
        if path.exists():
            return Template(path.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"Prompt template not found: {name}")


def format_rules() -> str:
    """Compile 快节奏意义切片规则：少标注、可读块、不做预售 Card。"""
    roles = ", ".join(sorted(VALID_BUFFER_ROLES))
    return f"""请遵循以下输出规则（快节奏意义切片；Harness 只守闸门）：

【目标】
把杂乱、长短不一的原文，切成**消化时读起来舒服**的意义块。块是原料，不是卡片草稿。

【块头 — 尽量短】
每块只用三段 YAML（Harness 落盘时自动补 created / updated / status）：
---
title: "短标题（说清本块讲什么）"
role: meaning-unit
source: "文件 / 章节或页码"
---
- `role` 常用：`meaning-unit`（默认）、`tension`（对立未和解）、`link-hypothesis`（弱关联，少用）。
- 完整可选集合：{roles}。不要为填表而换 role。
- **不要写**：created、updated、status、id、relations、Card 七型 type、proposed_card_type、proposed_domains（除非你极有把握且对 digest 有用）。
- source 含冒号/引号时用双引号包裹整串。

【正文 — 自由连贯，不填槽】
- 用自然段落写清：主张/机制 + 关键依据或数字 + 边界（若有）+ 1–2 条短摘录（可用 `>`）。
- **不要求** `### 核心表达 / 依据与细节 / …` 四级标题；需要分段时用任意小标题即可。
- 表图数字与观察默认写进所属块，不要另开空心 artifact。
- 禁止 `[[ ]]`；提及概念用加粗。

【切分节奏】
- 按意义切，不按「问题/主张/证据/限制」维度切薄片。
- 同一论证链写进同一块；本单元宜少而可读（常见 3–8 块，勿 15+ 标题壳）。
- 对立各写一块，再用 `tension` 记分歧；禁止和稀泥。
- 宁可少切，不要硬造；已切则宁厚勿空——质料供 digest **对着骨架滋养**，不是「一片预售一张 Card」。

【合格示例】
---
title: "教学反馈应指出可操作差距"
role: meaning-unit
source: "paper.pdf / §3.2 / pp.12-14"
---

　　教学反馈应优先指出可操作差距，而非仅给笼统评价。对照实验（N=120）比较「笼统赞扬」与「指出目标差距 + 下一步」；后一组修订成功率更高。作者将可操作差距定义为当前表现与成功标准之间可观察、可执行的差额。样本限于大学写作课，未讨论跨文化适用性。

> Feedback should name the actionable gap between current performance and the success criteria.
"""


def render_compile_prompt(units: list[dict], genre: str | None = None, deep: bool = False) -> str:
    name = f"compile-{genre or 'generic'}"
    try:
        template = _load_template(name)
    except FileNotFoundError:
        template = _load_template("compile-generic")
    units_render = []
    for idx, u in enumerate(units, 1):
        source = " / ".join(
            p for p in [u["source_path"].name, u.get("title", ""), u.get("section", ""), u.get("page_range", "")] if p
        )
        units_render.append({
            "index": idx,
            "total": len(units),
            "source": source,
            "char_count": u["char_count"],
            "text": u["text"],
        })
    return template.render(units=units_render, format_rules=format_rules(), deep=deep)


def render_digest_prompt(
    buffers: list,
    catalog: list | None = None,
    deep_cards: list | None = None,
    questions: list | None = None,
    *,
    bootstrap: bool = False,
    deferred_count: int = 0,
    index_excerpts: str = "",
    material_excerpts: str = "",
) -> str:
    template = _load_template("digest")
    catalog = catalog or []
    deep_cards = deep_cards or []
    return template.render(
        buffers=buffers,
        catalog=catalog,
        domain_catalog=[c for c in catalog if c.get("type") == "domain"],
        instance_catalog=[c for c in catalog if c.get("type") != "domain"],
        deep_cards=deep_cards,
        domain_deep=[c for c in deep_cards if c.get("type") == "domain"],
        instance_deep=[c for c in deep_cards if c.get("type") != "domain"],
        questions=questions or [],
        bootstrap=bootstrap,
        deferred_count=deferred_count,
        index_excerpts=index_excerpts,
        material_excerpts=material_excerpts,
    )


def render_construct_prompt(
    catalog: list | None = None,
    deep_cards: list | None = None,
    buffers: list | None = None,
    questions: list | None = None,
    *,
    lens: str = "cluster",
    signals: list | None = None,
    diagnose_mode: bool = False,
) -> str:
    name = "construct-diagnose" if diagnose_mode else "construct"
    template = _load_template(name)
    return template.render(
        catalog=catalog or [],
        deep_cards=deep_cards or [],
        buffers=buffers or [],
        questions=questions or [],
        lens=lens,
        signals=signals or [],
    )
