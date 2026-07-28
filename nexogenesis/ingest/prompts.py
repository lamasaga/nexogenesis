"""Prompt 模板加载与渲染。"""

from pathlib import Path

from jinja2 import Template

from nexogenesis.ingest import VALID_BUFFER_ROLES
from nexogenesis.schemas import CARD_TYPES


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
    roles = ", ".join(sorted(VALID_BUFFER_ROLES))
    card_types = ", ".join(CARD_TYPES)
    return f"""请遵循以下输出规则：
1. 每个质料单独输出为一个 YAML frontmatter + Markdown 正文块。
2. 使用 role（不是 Card type）标注材料用途，必须从以下集合选择：{roles}。
3. 默认按「意义单元」组织：一片围绕一个自足核心，依据/边界/摘录内嵌；禁止按 problem/claim/evidence 切成无核薄片。
4. 重要表格用 role: artifact-table，重要配图用 role: artifact-figure，各自独立成块。
5. 对立主张分别成 meaning-unit，另用 tension 记录分歧；禁止和稀泥成平衡观点。
6. 跨段/跨文「可能有关」写成 link-hypothesis（弱假设），不要写成 Card relations。
7. 可选 proposed_card_type（仅建议，digest 可改），取值：{card_types}。
8. 禁止使用 [[ ]] 链接；提及概念用加粗。禁止 frontmatter 写 id / relations / Card 七型 type。
9. source 必须精确（文件/章节/页码/图表编号）。含冒号、引号、井号时必须用双引号包裹整个字符串。
10. meaning-unit 正文必须使用且仅使用 Markdown 三级标题：### 核心表达 / ### 依据与细节 / ### 限制与边界 / ### 原文摘录；缺信息写「原文未提及：……」。
11. 块之间只用单独一行 --- 分隔；禁止 ---\n\n---；正文中不要出现单独成行的 ---（表格用 | --- | 即可）。
12. 宁可少拆，不要硬造；但每个已建质料应「宁厚勿空」——多留可复核的原文信息，供后续 digest 使用。
13. 原文保留（稍加强）：
    - 「依据与细节」尽量保留关键公式、符号定义、数据集/指标名、关键数值与对照条件（可条列，勿只写空泛转述）。
    - 「原文摘录」每个 meaning-unit 建议 2–3 条短摘录（每条一句或一小段，用 > 引用）；优先可核对主张的原句，勿整节粘贴。
    - artifact-table：优先完整 Markdown 表转写；文末可加「关键观察」1–3 句，并可附 1 条表注/原文说明摘录。
    - artifact-figure：除内容转写外，尽量保留轴含义、图注要点或作者对图的一句解释。

【合格示例 — 请严格模仿此结构】
---
title: "教学反馈应指出可操作差距"
role: meaning-unit
source: "paper.pdf / §3.2: Results / pp. 12-14"
genre: paper
perspective: external
proposed_card_type: claim
---
### 核心表达

　　教学反馈应优先指出可操作差距，而非仅给笼统评价。

### 依据与细节

　　对照实验（N=120）比较「笼统赞扬」与「指出目标差距 + 下一步动作」两组；后一组修订成功率更高。作者将可操作差距定义为当前表现与成功标准之间可观察、可执行的差额。

### 限制与边界

　　原文未提及：未讨论跨文化适用性；样本限于大学写作课。

### 原文摘录

> Feedback should name the actionable gap between current performance and the success criteria.
> "Vague praise did not reliably improve revision quality in our sample."
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
    # 兼容旧调用：cards= 全文列表
    return template.render(
        buffers=buffers,
        catalog=catalog or [],
        deep_cards=deep_cards or [],
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
