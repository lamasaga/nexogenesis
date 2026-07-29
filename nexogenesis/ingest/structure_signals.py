"""construct 诊断用的确定性结构信号（无向量库）。"""

from __future__ import annotations

from pathlib import Path

from nexogenesis.models import CardType, RelationType
from nexogenesis.store import Store
from nexogenesis.yaml_utils import split_frontmatter
from nexogenesis.ingest.edge_quality import edge_quality_signals


LENSES = ("cluster", "distinguish", "articulate", "cross_source")


def collect_structure_signals(
    store: Store,
    buffer_records: list[dict],
) -> dict[str, list[str]]:
    """返回各镜头下的信号列表（字符串，供报告与 prompt）。"""
    signals: dict[str, list[str]] = {k: [] for k in LENSES}

    # 边质量 / 枢纽稀缺 / seed 冻结（反馈：边数≠思想连通）
    for lens, items in edge_quality_signals(store).items():
        if lens in signals:
            signals[lens].extend(items)

    # --- cluster ---
    domain_ids = {cid for cid, c in store.cards.items() if c.type == CardType.DOMAIN}
    for cid, c in store.cards.items():
        if c.type == CardType.DOMAIN:
            members = [x for x in store.by_domain.get(cid, []) if x != cid]
            if not members:
                signals["cluster"].append(f"domain `{cid}` 无成员卡片（可能是空壳/标签型）")
            # 极短正文
            if c.body and len(c.body.strip()) < 40:
                signals["cluster"].append(f"domain `{cid}` 正文过短，可能缺少核心问题/边界/张力")
        else:
            for d in c.domains:
                if d not in store.cards:
                    signals["cluster"].append(f"`{cid}` 的 domains 引用不存在的 `{d}`")
                elif d not in domain_ids:
                    signals["cluster"].append(f"`{cid}` 的 `{d}` 不是 domain 卡")

    # 孤儿 / 链接空洞：非 domain 无 outgoing relations（汇总，避免刷屏）
    hollow: list[str] = []
    for cid, c in store.cards.items():
        if c.type == CardType.DOMAIN:
            continue
        if not c.relations:
            hollow.append(f"{cid}({c.type.value})")
    if hollow:
        show = hollow[:8]
        extra = len(hollow) - len(show)
        line = "无 outgoing relations（链接空洞）：" + ", ".join(f"`{x}`" for x in show)
        if extra > 0:
            line += f" …另有 {extra} 张"
        line += (
            "。优先补语义边（based-on/supports/involves）；"
            "空 relations 可用 seed-links 挂 domain，但勿把 applies-to 当完成态。"
        )
        signals["cluster"].append(line)
        signals["articulate"].append(line)

    # 领域有成员但成员彼此几乎无边 → 图能分区却难多跳
    for did in domain_ids:
        members = [x for x in store.by_domain.get(did, []) if x != did]
        if len(members) < 2:
            continue
        hollow_m = sum(
            1
            for m in members
            if m in store.cards and not store.cards[m].relations
        )
        if hollow_m >= max(2, (len(members) + 1) // 2):
            signals["articulate"].append(
                f"domain `{did}` 有 {len(members)} 个成员，其中 {hollow_m} 张无 relations——"
                "图谱偏「卡片柜」；本镜头优先为成员补 2–4 条语义边"
            )

    # --- distinguish ---
    conflict_ids = {cid for cid, c in store.cards.items() if c.type == CardType.CONFLICT}
    for cid, c in store.cards.items():
        if c.type == CardType.CONFLICT:
            involves = [r for r in c.relations if r.type == RelationType.INVOLVES]
            if not involves:
                only_domain = all(
                    r.type == RelationType.APPLIES_TO for r in c.relations
                ) if c.relations else True
                tip = (
                    "（目前多半只挂了 domain；须 involves 指向对立双方的 claim/model，"
                    "不要只写 applies-to 领域）"
                    if only_domain
                    else ""
                )
                signals["distinguish"].append(f"conflict `{cid}` 缺少 involves{tip}")
        for rel in c.relations:
            if rel.type != RelationType.CONFLICTS_WITH:
                continue
            # 是否存在以双方为 involves 的 conflict 卡
            covered = False
            for conf_id in conflict_ids:
                conf = store.cards[conf_id]
                involved = {
                    r.target for r in conf.relations if r.type == RelationType.INVOLVES
                }
                if cid in involved and rel.target in involved:
                    covered = True
                    break
            if not covered:
                signals["distinguish"].append(
                    f"`{cid}` conflicts-with `{rel.target}`，但尚无覆盖双方的 conflict 卡"
                )

    for b in buffer_records:
        if b.get("role") == "tension" and b.get("status") in ("scratch", "digested", ""):
            signals["distinguish"].append(
                f"tension Buffer 未升格候选：{b.get('path')}（status={b.get('status') or '?'}）"
            )

    # --- articulate ---
    for cid, c in store.cards.items():
        if len(c.relations) >= 8:
            signals["articulate"].append(
                f"`{cid}` outgoing relations={len(c.relations)}（可能过载，考虑抽 model）"
            )
        # 简单：多张卡互相指向形成团——度高且非 domain
        if c.type != CardType.DOMAIN and len(c.relations) >= 4:
            signals["articulate"].append(
                f"`{cid}` 关系较多，检查是否可抽成可复用 model/method"
            )

    for b in buffer_records:
        if b.get("role") in ("artifact-table", "artifact-figure") and b.get("status") == "digested":
            signals["articulate"].append(
                f"表/图已 digested，检查是否挂到解释结构：{b.get('path')}"
            )
        if b.get("role") == "link-hypothesis" and b.get("status") in ("scratch", "digested"):
            signals["articulate"].append(f"弱链假设待衔接：{b.get('path')}")

    # --- cross_source ---
    by_source: dict[str, list[str]] = {}
    for b in buffer_records:
        src = (b.get("source") or "").split("/")[0].strip() or "unknown"
        by_source.setdefault(src, []).append(b.get("path") or "")
    multi = {s: paths for s, paths in by_source.items() if len(paths) >= 2 and s != "unknown"}
    if len(multi) >= 2:
        signals["cross_source"].append(
            "存在 ≥2 个多片来源，可开跨源对照波："
            + "; ".join(f"{s}({len(p)}片)" for s, p in sorted(multi.items())[:8])
        )
    elif len(by_source) >= 2:
        signals["cross_source"].append(
            "Buffer 来自多个 source，可对照主题互补/对立："
            + ", ".join(sorted(by_source.keys())[:12])
        )
    else:
        signals["cross_source"].append("当前 Buffer 来源较单一；跨源镜头可暂缓或扩大材料后再跑")

    return signals


def render_diagnose_report(
    store: Store,
    buffer_records: list[dict],
    signals: dict[str, list[str]],
) -> str:
    lines = [
        "# construct 结构诊断报告（自动生成）",
        "",
        f"卡片数：{len(store.cards)}；Buffer 索引条数：{len(buffer_records)}",
        "",
        "## 卡片目录（无正文）",
    ]
    for cid, c in sorted(store.cards.items()):
        lines.append(f"- {cid} ({c.type.value}) {c.title} domains={list(c.domains)}")
    lines.append("")
    lines.append("## Buffer 索引（无全文）")
    for b in buffer_records:
        lines.append(
            f"- [{b.get('status')}] {b.get('role')} | {b.get('title')} | {b.get('path')}"
        )
    lines.append("")
    for lens in LENSES:
        lines.append(f"## 镜头 `{lens}`")
        items = signals.get(lens) or []
        if not items:
            lines.append("- （无确定性信号）")
        else:
            for it in items:
                lines.append(f"- {it}")
        lines.append("")
    lines.append("下一步：`python -m nexogenesis construct --lens <name>`，一次只跑一个镜头。")
    lines.append("禁止 `--lens all`。跨源请用 `--lens cross_source` 并依赖本报告点名的来源。")
    return "\n".join(lines) + "\n"


def suggest_ids_for_lens(
    store: Store,
    buffer_records: list[dict],
    signals: dict[str, list[str]],
    lens: str,
    *,
    max_cards: int = 8,
    max_buffers: int = 6,
) -> tuple[list[str], list[str]]:
    """从信号中粗提取本镜头应深读的 card id 与 buffer path。"""
    import re

    card_ids: list[str] = []
    buf_paths: list[str] = []
    blob = "\n".join(signals.get(lens) or [])
    # `id` 形式
    for m in re.finditer(r"`([^`]+)`", blob):
        token = m.group(1)
        if token in store.cards:
            card_ids.append(token)
        elif "05-Buffer/" in token or token.endswith(".md"):
            buf_paths.append(token)

    # tension / artifact buffers for distinguish/articulate
    if lens == "distinguish":
        for b in buffer_records:
            if b.get("role") == "tension":
                buf_paths.append(b["path"])
    if lens == "articulate":
        for b in buffer_records:
            if b.get("role") in ("artifact-table", "artifact-figure", "link-hypothesis"):
                buf_paths.append(b["path"])
    if lens == "cluster":
        for cid, c in store.cards.items():
            if c.type == CardType.DOMAIN:
                card_ids.append(cid)
    if lens == "cross_source":
        # 多带 meaning-unit digested
        for b in buffer_records:
            if b.get("role") == "meaning-unit":
                buf_paths.append(b["path"])

    # 去重保序
    def uniq(xs: list[str]) -> list[str]:
        seen = set()
        out = []
        for x in xs:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    card_ids = uniq(card_ids)[:max_cards]
    buf_paths = uniq(buf_paths)[:max_buffers]

    # 若仍空，兜底：domain 卡 + 若干 digested meaning-unit
    if not card_ids:
        card_ids = [cid for cid, c in store.cards.items() if c.type == CardType.DOMAIN][:max_cards]
    if not buf_paths:
        buf_paths = [
            b["path"]
            for b in buffer_records
            if b.get("status") == "digested" or b.get("role") == "tension"
        ][:max_buffers]

    return card_ids, buf_paths


def index_all_buffers(buffer_dir: Path, root: Path) -> list[dict]:
    from nexogenesis.ingest.context_pack import load_buffer_records

    paths: list[Path] = []
    if not buffer_dir.exists():
        return []
    for subdir in sorted(buffer_dir.iterdir()):
        if not subdir.is_dir() or subdir.name.startswith("_"):
            continue
        paths.extend(sorted(subdir.glob("*.md")))
    return load_buffer_records(paths, root)
