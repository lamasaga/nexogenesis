from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

LAYOUT_REL = Path(".nexogenesis/graph/layout.json")

_DOMAIN_RING_RADIUS = 340.0
_CLUSTER_RADIUS = 58.0


def _hash01(seed: str, salt: str) -> float:
    """id 哈希 → [0,1) 稳定伪随机值（跨进程确定）。"""
    h = hashlib.md5(f"{seed}:{salt}".encode("utf-8")).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def _node_position(node: dict, centers: dict[str, tuple[float, float]]) -> dict:
    domain = node["domains"][0] if node["domains"] else "_none"
    cx, cy = centers[domain]
    ang = _hash01(node["id"], "ang") * math.tau
    dist = 12.0 + (_hash01(node["id"], "dist") ** 0.6) * _CLUSTER_RADIUS
    return {
        "x": round(cx + math.cos(ang) * dist, 2),
        "y": round(cy + math.sin(ang) * dist * 0.85, 2),
    }


def compute_layout(nodes: list[dict]) -> dict[str, dict[str, float]]:
    """domain 聚簇布局：domain 环状均布，节点确定性散布于簇内。"""
    domains = sorted({(n["domains"] or ["_none"])[0] for n in nodes})
    centers: dict[str, tuple[float, float]] = {}
    for i, d in enumerate(domains):
        a = i / len(domains) * math.tau - math.pi / 2
        centers[d] = (_DOMAIN_RING_RADIUS * math.cos(a),
                      _DOMAIN_RING_RADIUS * math.sin(a) * 0.8)
    return {n["id"]: _node_position(n, centers) for n in nodes}


def load_layout(root: Path) -> dict[str, dict[str, float]]:
    path = root / LAYOUT_REL
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_layout(root: Path, pos: dict[str, dict[str, float]]) -> None:
    path = root / LAYOUT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pos, ensure_ascii=False, indent=1), encoding="utf-8")


def ensure_layout(root: Path, nodes: list[dict]) -> dict[str, dict[str, float]]:
    """读缓存；缺失节点按当前 domain 环补算并落盘。已有坐标永不变更。"""
    root = root.resolve()
    cached = load_layout(root)
    node_ids = {n["id"] for n in nodes}
    pos = {cid: p for cid, p in cached.items() if cid in node_ids}
    missing = [n for n in nodes if n["id"] not in pos]
    if missing:
        fresh = compute_layout(nodes)
        for n in missing:
            pos[n["id"]] = fresh[n["id"]]
        save_layout(root, pos)
    return pos
