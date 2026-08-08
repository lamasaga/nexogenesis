import type { ActivationEngine } from "../activation/engine";
import { THEME } from "../activation/theme";
import { controlPoint, qPoint, type Fiber } from "./bundles";
import type { Camera } from "./camera";
import type { GraphNode } from "./types";

const SEG = 22;

export interface Scene {
  nodes: GraphNode[];
  fibers: Fiber[];
  clusterCenters: Map<string, { x: number; y: number }>;
  domains: Map<string, { x: number; y: number; label: string }>;
}

/** 从图数据派生场景（簇心 = 各 domain 节点坐标均值；domain 标签沿径向外置防碰撞） */
export function buildScene(nodes: GraphNode[], fibers: Fiber[]): Scene {
  const sums = new Map<string, { x: number; y: number; n: number }>();
  for (const nd of nodes) {
    const d = nd.domains[0] ?? "_none";
    const s = sums.get(d) ?? { x: 0, y: 0, n: 0 };
    s.x += nd.x; s.y += nd.y; s.n++;
    sums.set(d, s);
  }
  // 全图质心：标签沿「簇心 → 外侧」径向摆放
  let gx = 0, gy = 0;
  for (const nd of nodes) { gx += nd.x; gy += nd.y; }
  gx /= nodes.length; gy /= nodes.length;
  const clusterCenters = new Map<string, { x: number; y: number }>();
  const domains = new Map<string, { x: number; y: number; label: string }>();
  for (const [d, s] of sums) {
    const c = { x: s.x / s.n, y: s.y / s.n };
    clusterCenters.set(d, c);
    let dx = c.x - gx, dy = c.y - gy;
    const len = Math.hypot(dx, dy);
    if (len < 1) { dx = 0; dy = -1; } else { dx /= len; dy /= len; }
    const domainNode = nodes.find((nd) => nd.id === d);
    domains.set(d, {
      x: c.x + dx * 95,
      y: c.y + dy * 95,
      label: domainNode?.title ?? d,
    });
  }
  return { nodes, fibers, clusterCenters, domains };
}

function strandPath(
  ctx: CanvasRenderingContext2D, f: Fiber, scene: Scene, offset: number
): void {
  const cp = controlPoint(f, scene.clusterCenters);
  const dx = f.b.x - f.a.x;
  const dy = f.b.y - f.a.y;
  const len = Math.hypot(dx, dy) || 1;
  const cx = cp.x + offset * (-dy / len);
  const cy = cp.y + offset * (dx / len);
  ctx.moveTo(f.a.x, f.a.y);
  ctx.quadraticCurveTo(cx, cy, f.b.x, f.b.y);
}

/** 静息层：全部纤维 + 突触小结 + 区域光晕（世界坐标，离屏缓存） */
export function drawRestLayer(
  ctx: CanvasRenderingContext2D, scene: Scene, now: number
): void {
  for (const f of scene.fibers) {
    for (const st of f.strands) {
      const breathe = 0.75 + 0.25 * Math.sin(now / 1.6 + st.phase);
      const alpha = (f.intra ? THEME.fibers.baseAlphaIntra : THEME.fibers.baseAlphaInter) * breathe;
      const [r, g, b] = f.relationColor;
      ctx.strokeStyle = `rgba(${r},${g},${b},${alpha})`;
      ctx.lineWidth = f.intra ? 0.9 : 1.3;
      ctx.beginPath();
      strandPath(ctx, f, scene, st.offset);
      ctx.stroke();
    }
  }
  for (const [, c] of scene.clusterCenters) {
    const grd = ctx.createRadialGradient(c.x, c.y, 0, c.x, c.y, 95);
    grd.addColorStop(0, "rgba(86,222,208,0.05)");
    grd.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = grd;
    ctx.beginPath();
    ctx.arc(c.x, c.y, 95, 0, Math.PI * 2);
    ctx.fill();
  }
  for (const nd of scene.nodes) {
    ctx.fillStyle = "rgba(150,238,224,0.75)";
    ctx.beginPath();
    ctx.arc(nd.x, nd.y, 2.6, 0, Math.PI * 2);
    ctx.fill();
  }
}

/** 激活层：活跃束逐段顺序点亮 + 节点光晕（每帧） */
export function drawActivationLayer(
  ctx: CanvasRenderingContext2D, scene: Scene, engine: ActivationEngine, now: number
): void {
  for (const f of scene.fibers) {
    const heat = engine.heatOf(f.domainKey, now);
    if (!heat) continue;
    for (const st of f.strands) {
      const cp = controlPoint(f, scene.clusterCenters);
      const dx = f.b.x - f.a.x;
      const dy = f.b.y - f.a.y;
      const len = Math.hypot(dx, dy) || 1;
      const ccx = cp.x + st.offset * (-dy / len);
      const ccy = cp.y + st.offset * (dx / len);
      const front = Math.max(0, heat.front - st.delay);
      let px = f.a.x, py = f.a.y;
      const [r, g, b] = heat.color;
      for (let s = 1; s <= SEG; s++) {
        const q = s / SEG;
        const p = qPoint(f.a.x, f.a.y, ccx, ccy, f.b.x, f.b.y, q);
        const passed = front - (s - 0.5) / SEG;
        const breathe = 0.75 + 0.25 * Math.sin(now / 1.6 + st.phase);
        const base = f.intra ? THEME.fibers.baseAlphaIntra : THEME.fibers.baseAlphaInter;
        const a = passed <= 0 ? base * breathe : base + Math.min(1, passed * 6) * 0.75;
        const hot = Math.max(0, 1 - Math.abs(passed) * 8);
        ctx.strokeStyle = `rgba(${Math.min(255, r + hot * 60)},${g},${b},${Math.min(1, a) * heat.fade})`;
        ctx.lineWidth = 1.3 + hot * 1.8;
        ctx.beginPath();
        ctx.moveTo(px, py);
        ctx.lineTo(p.x, p.y);
        ctx.stroke();
        px = p.x; py = p.y;
      }
      if (front >= 1) engine.pokeFromRenderer(f.b.id, 0.9 * heat.fade);
      if (front > 0.05) engine.pokeFromRenderer(f.a.id, 0.5 * heat.fade);
    }
  }
  for (const nd of scene.nodes) {
    const act = engine.nodeActOf(nd.id);
    if (act <= 0.25) continue;
    const radius = 2.6 + act * 2.2;
    const grd = ctx.createRadialGradient(nd.x, nd.y, 0, nd.x, nd.y, radius * 4);
    grd.addColorStop(0, `rgba(255,205,135,${act * 0.8})`);
    grd.addColorStop(1, "rgba(255,205,135,0)");
    ctx.fillStyle = grd;
    ctx.beginPath();
    ctx.arc(nd.x, nd.y, radius * 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = `rgba(255,215,155,${Math.min(1, act)})`;
    ctx.beginPath();
    ctx.arc(nd.x, nd.y, radius, 0, Math.PI * 2);
    ctx.fill();
  }
}

/** 标注层：domain 标签恒显；卡片标题 act 超阈值才浮现（每帧） */
export function drawLabelLayer(
  ctx: CanvasRenderingContext2D, scene: Scene, engine: ActivationEngine,
  camera: Camera, hoverId: string | null
): void {
  const fs = 13 / camera.scale;
  ctx.textAlign = "center";
  for (const [, dm] of scene.domains) {
    ctx.font = `${fs}px "Microsoft YaHei", sans-serif`;
    ctx.fillStyle = "rgba(170,215,212,0.75)";
    ctx.fillText(dm.label, dm.x, dm.y);
  }
  ctx.textAlign = "left";
  const titleFs = 12 / camera.scale;
  ctx.font = `${titleFs}px "Microsoft YaHei", sans-serif`;
  const labeled = scene.nodes
    .map((nd) => ({ nd, act: Math.max(engine.nodeActOf(nd.id), nd.id === hoverId ? 1 : 0) }))
    .filter((x) => x.act > THEME.node.labelThreshold)
    .sort((a, b) => b.act - a.act)
    .slice(0, 24); // 碰撞回避的预算上限
  for (const { nd, act } of labeled) {
    ctx.fillStyle = `rgba(255,230,190,${Math.min(1, (act - THEME.node.labelThreshold) * 1.8)})`;
    ctx.fillText(nd.title, nd.x + 9 / camera.scale, nd.y + 4 / camera.scale);
  }
}
