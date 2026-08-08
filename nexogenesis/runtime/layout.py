from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

LAYOUT_REL = Path(".nexogenesis/graph/layout.json")

# ---- 力导向参数（定调：关联吸引力 > 节点排斥力 > 图向心力）----
_REST_LEN = 38.0        # 边静息长度
_SPRING_K = 0.055       # 边吸引力系数（最强）
_REPEL_K = 380.0        # 排斥强度 F=K/d²（截断半径内）
_REPEL_CUTOFF = 90.0    # 排斥作用半径（均匀网格加速）
_REPEL_MAX = 4.0        # 单节点单步排斥力上限
_GRAVITY_K = 0.006      # 向心引力系数（最弱）
_DAMPING = 0.85         # 速度阻尼
_MAX_STEP = 6.0         # 单步位移上限
_FULL_ITERS = 600       # 全量模拟迭代数
_GROW_ITERS = 120       # 增量松弛迭代数
_SOFT_PIN = 0.15        # 增量时已有节点位移权重（软钉）


def _hash01(seed: str, salt: str) -> float:
    """id 哈希 → [0,1) 稳定伪随机值（跨进程确定）。"""
    h = hashlib.md5(f"{seed}:{salt}".encode("utf-8")).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def _initial_positions(nodes: list[dict]) -> dict[str, list[float]]:
    """确定性初始散布：大圆环带 + 哈希抖动，避免对称坍缩与重叠起点。"""
    n = max(1, len(nodes))
    ring = 60.0 + 14.0 * math.sqrt(n)
    pos: dict[str, list[float]] = {}
    for i, nd in enumerate(nodes):
        a = i / n * math.tau + _hash01(nd["id"], "init-a") * 0.5
        r = ring * (0.5 + 0.5 * _hash01(nd["id"], "init-r"))
        pos[nd["id"]] = [r * math.cos(a), r * math.sin(a)]
    return pos


def simulate(
    nodes: list[dict],
    edges: list[dict],
    iterations: int,
    initial: dict[str, list[float]] | None = None,
    soft_pin: set[str] | None = None,
) -> dict[str, dict[str, float]]:
    """力导向模拟（确定性：固定迭代数 + 哈希初始位置 + 固定遍历顺序）。

    三类力：边弹簧吸引（最强）> 截断库仑排斥（均匀网格加速）> 质心向心力（最弱）。
    soft_pin 中的节点以 _SOFT_PIN 权重位移（增量布局时保持旧图稳定）。
    """
    ids = [n["id"] for n in nodes]
    idx_of = {cid: i for i, cid in enumerate(ids)}
    pos = _initial_positions(nodes)
    if initial:
        for cid, p in initial.items():
            if cid in pos:
                pos[cid] = [p[0], p[1]]
    vel = {cid: [0.0, 0.0] for cid in ids}
    pairs = [(idx_of[e["from"]], idx_of[e["to"]])
             for e in edges if e["from"] in idx_of and e["to"] in idx_of]
    pin = soft_pin or set()

    for it in range(iterations):
        alpha = 1.0 - 0.95 * (it / max(1, iterations))  # 退火：步长逐渐收敛
        forces = {cid: [0.0, 0.0] for cid in ids}

        # -- 排斥力：均匀网格，仅作用截断半径内（O(n·k)）--
        grid: dict[tuple[int, int], list[int]] = {}
        for cid in ids:
            i = idx_of[cid]
            cell = (int(pos[cid][0] // _REPEL_CUTOFF),
                    int(pos[cid][1] // _REPEL_CUTOFF))
            grid.setdefault(cell, []).append(i)
        for cid in ids:
            i = idx_of[cid]
            cx = int(pos[cid][0] // _REPEL_CUTOFF)
            cy = int(pos[cid][1] // _REPEL_CUTOFF)
            for dcx in (-1, 0, 1):
                for dcy in (-1, 0, 1):
                    for j in grid.get((cx + dcx, cy + dcy), []):
                        if j <= i:
                            continue
                        other = ids[j]
                        dx = pos[cid][0] - pos[other][0]
                        dy = pos[cid][1] - pos[other][1]
                        d2 = dx * dx + dy * dy
                        if d2 > _REPEL_CUTOFF * _REPEL_CUTOFF:
                            continue
                        dist = math.sqrt(d2) or 0.01
                        f = min(_REPEL_MAX, _REPEL_K / d2) * alpha
                        fx, fy = f * dx / dist, f * dy / dist
                        forces[cid][0] += fx
                        forces[cid][1] += fy
                        forces[other][0] -= fx
                        forces[other][1] -= fy

        # -- 边弹簧吸引力（最强）--
        for i, j in pairs:
            a, b = ids[i], ids[j]
            dx = pos[b][0] - pos[a][0]
            dy = pos[b][1] - pos[a][1]
            dist = math.hypot(dx, dy) or 0.01
            f = _SPRING_K * (dist - _REST_LEN) * alpha
            fx, fy = f * dx / dist, f * dy / dist
            forces[a][0] += fx
            forces[a][1] += fy
            forces[b][0] -= fx
            forces[b][1] -= fy

        # -- 向心力（最弱）：朝向当前质心 --
        gx = sum(pos[c][0] for c in ids) / len(ids)
        gy = sum(pos[c][1] for c in ids) / len(ids)
        for cid in ids:
            forces[cid][0] += _GRAVITY_K * (gx - pos[cid][0]) * alpha
            forces[cid][1] += _GRAVITY_K * (gy - pos[cid][1]) * alpha

        # -- 积分：阻尼 + 位移上限 + 软钉 --
        for cid in ids:
            w = _SOFT_PIN if cid in pin else 1.0
            vx = (vel[cid][0] + forces[cid][0]) * _DAMPING
            vy = (vel[cid][1] + forces[cid][1]) * _DAMPING
            step = math.hypot(vx, vy)
            if step > _MAX_STEP:
                vx, vy = vx * _MAX_STEP / step, vy * _MAX_STEP / step
            vel[cid] = [vx, vy]
            pos[cid][0] += vx * w
            pos[cid][1] += vy * w

    return {cid: {"x": round(pos[cid][0], 2), "y": round(pos[cid][1], 2)}
            for cid in ids}


def compute_layout(nodes: list[dict], edges: list[dict]) -> dict[str, dict[str, float]]:
    """全量力导向布局（Obsidian 式：结构驱动，枢纽聚中、叶子散开）。"""
    return simulate(nodes, edges, _FULL_ITERS)


def load_layout(root: Path) -> dict[str, dict[str, float]]:
    path = root / LAYOUT_REL
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_layout(root: Path, pos: dict[str, dict[str, float]]) -> None:
    path = root / LAYOUT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pos, ensure_ascii=False, indent=1), encoding="utf-8")


def ensure_layout(
    root: Path, nodes: list[dict], edges: list[dict]
) -> dict[str, dict[str, float]]:
    """读缓存；有缺时增量松弛：新节点播在邻近簇心附近，旧节点软钉保持地图稳定。"""
    root = root.resolve()
    cached = load_layout(root)
    node_ids = {n["id"] for n in nodes}
    pos = {cid: p for cid, p in cached.items() if cid in node_ids}
    missing = [n for n in nodes if n["id"] not in pos]
    if not missing:
        return pos
    if not pos:
        # 首次：全量模拟
        pos = compute_layout(nodes, edges)
        save_layout(root, pos)
        return pos
    # 增量：新节点初始位置 = 同 domain 已有节点质心 + 哈希抖动
    domain_centers: dict[str, list[float]] = {}
    domain_counts: dict[str, int] = {}
    domain_of = {n["id"]: (n["domains"] or ["_none"])[0] for n in nodes}
    for cid, p in pos.items():
        d = domain_of.get(cid, "_none")
        c = domain_centers.setdefault(d, [0.0, 0.0])
        c[0] += p["x"]
        c[1] += p["y"]
        domain_counts[d] = domain_counts.get(d, 0) + 1
    for d, c in domain_centers.items():
        c[0] /= domain_counts[d]
        c[1] /= domain_counts[d]
    initial: dict[str, list[float]] = {cid: [p["x"], p["y"]]
                                       for cid, p in pos.items()}
    for n in missing:
        d = domain_of.get(n["id"], "_none")
        c = domain_centers.get(d, [0.0, 0.0])
        ang = _hash01(n["id"], "grow-a") * math.tau
        r = 20.0 + 30.0 * _hash01(n["id"], "grow-r")
        initial[n["id"]] = [c[0] + r * math.cos(ang), c[1] + r * math.sin(ang)]
    pos = simulate(nodes, edges, _GROW_ITERS,
                   initial=initial, soft_pin=set(pos))
    save_layout(root, pos)
    return pos
