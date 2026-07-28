from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

from nexogenesis.graph.build import load_snapshot, rebuild_graph
from nexogenesis.graph.model import GraphSnapshot
from nexogenesis.models import CardType, RelationType
from nexogenesis.store import Store, WIKILINK_RE
from nexogenesis.yaml_utils import atomic_write_file


def _undirected_adj(snapshot: GraphSnapshot) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = {}
    for e in snapshot.edges:
        adj.setdefault(e.from_id, set()).add(e.to_id)
        adj.setdefault(e.to_id, set()).add(e.from_id)
    return adj


def _connected_components(nodes: set[str], adj: dict[str, set[str]]) -> list[set[str]]:
    seen: set[str] = set()
    comps: list[set[str]] = []
    for start in nodes:
        if start in seen:
            continue
        comp: set[str] = set()
        q = deque([start])
        while q:
            n = q.popleft()
            if n in seen:
                continue
            seen.add(n)
            comp.add(n)
            for nb in adj.get(n, ()):
                if nb in nodes and nb not in seen:
                    q.append(nb)
        comps.append(comp)
    return comps


def find_bridge_nodes(
    store: Store,
    snapshot: GraphSnapshot,
    *,
    max_nodes: int = 120,
) -> list[str]:
    """小规模图：删掉节点后连通分量增加则为桥接点。"""
    active = {
        cid
        for cid, c in store.cards.items()
        if c.lifecycle.value != "archived"
    }
    if len(active) > max_nodes or len(active) < 3:
        return []

    uadj = _undirected_adj(snapshot)
    base = _connected_components(active, uadj)
    base_count = len(base)

    bridges: list[str] = []
    for nid in sorted(active):
        reduced = {n for n in active if n != nid}
        radj = {k: v & reduced for k, v in uadj.items() if k in reduced}
        if len(_connected_components(reduced, radj)) > base_count:
            bridges.append(nid)
    return bridges


def load_structure_ops(root: Path) -> list[dict[str, Any]]:
    path = root / ".nexogenesis" / "graph" / "reports" / "structure_ops.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("ops") or [])


def structure_ops_to_signals(ops: list[dict[str, Any]]) -> dict[str, list[str]]:
    """将 structure_ops 映射到 construct 镜头信号。"""
    signals: dict[str, list[str]] = {
        "cluster": [],
        "distinguish": [],
        "articulate": [],
        "cross_source": [],
    }
    for op in ops:
        kind = op.get("op", "")
        reason = op.get("reason", "")
        cards = op.get("cards") or []
        card_txt = ", ".join(f"`{c}`" for c in cards)
        line = f"[graph-analyze] {kind}: {reason} → {card_txt}"
        if kind == "suggest_conflict_card":
            signals["distinguish"].append(line)
        elif kind == "suggest_link_or_enrich":
            signals["cluster"].append(line)
            signals["articulate"].append(line)
        else:
            signals["cluster"].append(line)
    return signals


def merge_structure_signals(
    lens_signals: dict[str, list[str]],
    graph_signals: dict[str, list[str]],
) -> dict[str, list[str]]:
    out = {k: list(v) for k, v in lens_signals.items()}
    for lens, items in graph_signals.items():
        out.setdefault(lens, [])
        for it in items:
            if it not in out[lens]:
                out[lens].append(it)
    return out


def write_structure_ops_batch_draft(root: Path, ops: list[dict[str, Any]]) -> Path:
    """生成结构提案 batch 草稿（须人工/Agent 补全 writes 后再 apply）。"""
    out_dir = root / ".nexogenesis" / "tmp" / "construct"
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 结构提案 batch 草稿（不可直接 apply）",
        "",
        "将下方 structure_ops 转为标准 write --batch YAML 后，经 construct --apply 或 --auto 落盘。",
        "",
        "```yaml",
        "operation:",
        "  id: construct-from-graph-ops-DRAFT",
        "  source: graph analyze",
        "  approved_by: user",
        "writes: []  # 须按 ops 填写 enrich / conflict / relations",
        "```",
        "",
        "## structure_ops",
        "",
    ]
    for op in ops[:20]:
        lines.append(f"- **{op.get('op')}**: {op.get('reason')} → {op.get('cards')}")
    lines.append("")
    path = out_dir / "structure-ops-draft.md"
    atomic_write_file(path, "\n".join(lines))
    return path


def analyze_graph(root: Path, *, rebuild: bool = False) -> dict[str, Any]:
    root = root.resolve()
    store = Store(root / "01-Cards").load()
    snapshot = load_snapshot(root)
    if snapshot is None or rebuild:
        snapshot = rebuild_graph(root)

    orphans: list[dict[str, str]] = []
    empty_domains: list[str] = []
    conflict_gaps: list[dict[str, Any]] = []
    no_relation: list[str] = []

    conflict_ids = {cid for cid, c in store.cards.items() if c.type == CardType.CONFLICT}

    for cid, c in store.cards.items():
        if c.type == CardType.DOMAIN:
            members = [x for x in store.by_domain.get(cid, []) if x != cid]
            if not members:
                empty_domains.append(cid)
            continue
        if not c.relations:
            no_relation.append(cid)
            if not (c.body and WIKILINK_RE.search(c.body)):
                orphans.append({"id": cid, "type": c.type.value})

    for cid, c in store.cards.items():
        for rel in c.relations:
            if rel.type != RelationType.CONFLICTS_WITH:
                continue
            if rel.target not in store.cards:
                continue
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
                conflict_gaps.append({
                    "from": cid,
                    "to": rel.target,
                    "suggest": "suggest_conflict_card",
                })

    bridges = find_bridge_nodes(store, snapshot) if snapshot else []

    structure_ops: list[dict[str, Any]] = []
    for g in conflict_gaps:
        structure_ops.append({
            "op": "suggest_conflict_card",
            "reason": f"`{g['from']}` conflicts-with `{g['to']}` 无 covering conflict",
            "cards": [g["from"], g["to"]],
        })
    for oid in orphans[:20]:
        structure_ops.append({
            "op": "suggest_link_or_enrich",
            "reason": "无 outgoing relations 且无正文 wikilink",
            "cards": [oid["id"]],
        })
    for bid in bridges[:10]:
        structure_ops.append({
            "op": "suggest_review_bridge",
            "reason": "桥接点：删除后图可能分裂，检查是否应抽 model 或合并",
            "cards": [bid],
        })

    metrics = {
        "node_count": len(store.cards),
        "edge_count": snapshot.edge_count if snapshot else 0,
        "orphan_count": len(orphans),
        "empty_domain_count": len(empty_domains),
        "conflict_gap_count": len(conflict_gaps),
        "no_relation_count": len(no_relation),
        "bridge_count": len(bridges),
        "orphans": orphans,
        "empty_domains": empty_domains,
        "conflict_gaps": conflict_gaps,
        "bridges": bridges,
    }

    reports_dir = root / ".nexogenesis" / "graph" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_file(
        reports_dir / "metrics.json",
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
    )
    atomic_write_file(
        reports_dir / "structure_ops.json",
        json.dumps({"ops": structure_ops}, ensure_ascii=False, indent=2) + "\n",
    )

    lines = [
        "# 图分析摘要（自动生成）",
        "",
        f"- 节点：{metrics['node_count']}；边：{metrics['edge_count']}",
        f"- orphan 候选：{metrics['orphan_count']}",
        f"- 空 domain：{metrics['empty_domain_count']}",
        f"- conflict 缺口：{metrics['conflict_gap_count']}",
        f"- 桥接点：{metrics['bridge_count']}",
        "",
    ]
    if structure_ops:
        lines.append("## 结构提案（须转 batch 后写入）")
        for op in structure_ops[:15]:
            lines.append(f"- **{op['op']}**：{op['reason']} → {op.get('cards')}")
    else:
        lines.append("（无确定性结构提案）")
    lines.append("")
    atomic_write_file(reports_dir / "latest-summary.md", "\n".join(lines))
    write_structure_ops_batch_draft(root, structure_ops)

    return metrics
