"""Prompt 模板加载与渲染。"""

from pathlib import Path

from jinja2 import Template

from nexogenesis.ingest import VALID_BUFFER_TYPES


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
    types = ", ".join(sorted(VALID_BUFFER_TYPES))
    return f"""请遵循以下输出规则：
1. 每个碎片单独输出为一个 YAML frontmatter + Markdown 正文块。
2. 为每个碎片指定一个暂定 type，必须从以下 7 个类型中选择：{types}。
   若无法判定 type，先放入 claim（并标注为 seed 成熟度）。
3. 禁止使用 [[ ]] 链接；提及已有概念时用加粗即可。
4. source 字段必须精确标注原始来源。
5. frontmatter 增加 genre 字段；涉及作者本人作品时增加 perspective: self，外部作品为 perspective: external。
6. 可选字段 proposed_domains（列表）和 proposed_maturity（seed/growing/mature）。
7. 宁可少拆，不要硬造；允许拆解不完整。"""


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
