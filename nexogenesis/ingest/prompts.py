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
    """Compile：高效保质料切片。Harness 已开阅读窗；模型只做窗内压缩命名。"""
    roles = ", ".join(("meaning-unit", "tension", "link-hypothesis"))
    return f"""【你的唯一任务】对本阅读窗产出 **1～6** 个有意义命名、**含质料**的 Buffer。
Harness 已按结构切好窗；不要重规划全书、不要填卡片槽、不要预售 Card。

【块格式】每块仅三行头 + 正文（落盘时自动补日期/status）：
---
title: "说清本块讲什么"
role: meaning-unit
source: "与窗来源一致，可加小节名"
---
　　连贯段落：机制/主张 + 关键条件或数字 +（若有）边界 + 1～2 句短摘录（可用 >）。
常用 role：{roles}（完整枚举见系统；勿为填表换 role）。
禁止：created/updated/status、id、relations、Card type、[[ ]]、空心标题壳。

【质料标准】
- 消化阶段应能直接把机制与事实并入 Card；省略废话与重复，**不要抽成更短的空摘要**。
- 块数按内容定（1～6）；宁少而厚，勿维度薄片（problem/claim/evidence 分片）。
- 表图数字默认写进块内。

【示例】
---
title: "教学反馈应指出可操作差距"
role: meaning-unit
source: "paper.pdf / §3.2"
---

　　教学反馈应优先指出可操作差距。对照实验（N=120）中，「指出目标差距+下一步」组修订成功率高于笼统赞扬。可操作差距=当前表现与成功标准间可观察差额。样本限于大学写作课。

> Feedback should name the actionable gap between current performance and the success criteria.
"""


def _load_shared_fragment(name: str) -> str:
    """加载 schemes/default/prompts/shared/ 下的共享片段。"""
    path = DEFAULT_PROMPTS_DIR / "shared" / f"{name}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Shared prompt fragment not found: {name}")


def card_cheatsheet() -> str:
    """七型卡片结构速查，注入 digest/construct/emerge prompt。"""
    return _load_shared_fragment("card-cheatsheet")


def quality_contract() -> str:
    """质料密度与反模式共享约束。"""
    return _load_shared_fragment("quality-contract")


def write_discipline() -> str:
    """写入与权限纪律共享约束。"""
    return _load_shared_fragment("write-discipline")


def profile_update_rule() -> str:
    """领域 Profile 更新规则。"""
    return _load_shared_fragment("profile-update-rule")


def render_compile_prompt(units: list[dict], genre: str | None = None, deep: bool = False) -> str:
    name = f"compile-{genre or 'generic'}"
    try:
        template = _load_template(name)
    except FileNotFoundError:
        template = _load_template("compile-generic")
    units_render = []
    for idx, u in enumerate(units, 1):
        source = " / ".join(
            p for p in [
                Path(u["source_path"]).name if u.get("source_path") else "",
                u.get("title", ""),
                u.get("section", ""),
                u.get("page_range", ""),
            ] if p
        )
        units_render.append({
            "index": idx,
            "total": len(units),
            "source": source,
            "char_count": u["char_count"],
            "text": u["text"],
            "title": u.get("title") or "",
            "section": u.get("section") or "",
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
        card_cheatsheet=card_cheatsheet(),
        quality_contract=quality_contract(),
        write_discipline=write_discipline(),
        profile_update_rule=profile_update_rule(),
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
        card_cheatsheet=card_cheatsheet(),
        quality_contract=quality_contract(),
        write_discipline=write_discipline(),
        profile_update_rule=profile_update_rule(),
    )
