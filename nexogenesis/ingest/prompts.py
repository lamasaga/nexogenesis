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
12. 宁可少拆，不要硬造。

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

　　教学反馈应优先指出可操作差距。

### 依据与细节

　　原文通过对照实验支持该主张。

### 限制与边界

　　原文未提及：未讨论跨文化适用性。

### 原文摘录

> feedback should name the actionable gap
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


def render_digest_prompt(buffers: list, cards: list, questions: list) -> str:
    template = _load_template("digest")
    return template.render(buffers=buffers, cards=cards, questions=questions)


def render_construct_prompt(cards: list, buffers: list, questions: list) -> str:
    template = _load_template("construct")
    return template.render(cards=cards, buffers=buffers, questions=questions)
