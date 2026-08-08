import { useEffect, useRef } from "react";
import { ActivationEngine } from "../activation/engine";
import { THEME } from "../activation/theme";
import { buildFibers } from "./bundles";
import { Camera } from "./camera";
import { buildScene, drawActivationLayer, drawLabelLayer, drawRestLayer } from "./render";
import type { GraphData, GraphNode } from "./types";

interface Props {
  data: GraphData;
  engine: ActivationEngine;
  onNodeClick: (id: string) => void;
}

export function GraphCanvas({ data, engine, onNodeClick }: Props) {
  const restRef = useRef<HTMLCanvasElement>(null);
  const actRef = useRef<HTMLCanvasElement>(null);
  const labelRef = useRef<HTMLCanvasElement>(null);
  const cameraRef = useRef(new Camera(0, 0, 1));
  const hoverRef = useRef<string | null>(null);
  const dragRef = useRef<{ x: number; y: number; moved: boolean } | null>(null);

  useEffect(() => {
    const { fibers } = buildFibers(data);
    const scene = buildScene(data.nodes, fibers);
    const camera = cameraRef.current;
    let raf = 0;
    let last = performance.now();
    const t0 = last;

    // 初始取景：整图居中
    const pad = 200;
    const xs = data.nodes.map((n) => n.x);
    const ys = data.nodes.map((n) => n.y);
    const minX = Math.min(...xs) - pad, maxX = Math.max(...xs) + pad;
    const minY = Math.min(...ys) - pad, maxY = Math.max(...ys) + pad;
    const host = restRef.current!.parentElement!;
    const fit = () => {
      const w = host.clientWidth, h = host.clientHeight;
      camera.scale = Math.min(Camera.MAX_SCALE, Math.max(Camera.MIN_SCALE,
        Math.min(w / (maxX - minX), h / (maxY - minY)) * 0.95));
      camera.x = (minX + maxX) / 2;
      camera.y = (minY + maxY) / 2;
    };
    fit();
    // 走查参数：?scale=&x=&y= 指定初始相机（截图验证用）
    {
      const q = new URLSearchParams(window.location.search);
      if (q.get("scale")) {
        camera.scale = Math.min(Camera.MAX_SCALE, Math.max(Camera.MIN_SCALE, parseFloat(q.get("scale")!)));
        camera.x = parseFloat(q.get("x") ?? "0");
        camera.y = parseFloat(q.get("y") ?? "0");
      }
    }

    // 静息层策略（方案 2）：视口尺寸离屏缓存。
    // 交互中按相机差量贴图（保帧率）；相机静止 200ms 后按当前相机
    // 以设备像素重渲染——任何缩放倍率下都恢复矢量级清晰。
    const off = document.createElement("canvas");
    const offCam = new Camera(camera.x, camera.y, camera.scale);
    let restDirty = true;
    let camMovedAt = 0;
    let prevCam = { x: camera.x, y: camera.y, scale: camera.scale };

    const renderRest = (pw: number, ph: number, w: number, h: number, dpr: number, now: number) => {
      off.width = pw;
      off.height = ph;
      const c = off.getContext("2d")!;
      c.setTransform(dpr * camera.scale, 0, 0, dpr * camera.scale,
        dpr * (w / 2 - camera.x * camera.scale),
        dpr * (h / 2 - camera.y * camera.scale));
      drawRestLayer(c, scene, now);
      offCam.x = camera.x; offCam.y = camera.y; offCam.scale = camera.scale;
    };

    const frame = (nowMs: number) => {
      const now = (nowMs - t0) / 1000;
      const dt = Math.min(0.1, (nowMs - last) / 1000);
      last = nowMs;
      engine.decay(dt);

      // 相机变动检测：标记脏 + 记录最近变动时刻
      if (camera.x !== prevCam.x || camera.y !== prevCam.y || camera.scale !== prevCam.scale) {
        restDirty = true;
        camMovedAt = nowMs;
        prevCam = { x: camera.x, y: camera.y, scale: camera.scale };
      }

      const w = host.clientWidth, h = host.clientHeight;
      const dpr = window.devicePixelRatio || 1;
      // dpr 非整数（1.25/1.5）时 w*dpr 是小数：必须取整后比较，
      // 否则每帧都判定尺寸变化 → 画布清空 + 全量重绘（帧率崩塌、画面抖动）
      const pw = Math.max(1, Math.round(w * dpr));
      const ph = Math.max(1, Math.round(h * dpr));
      for (const ref of [restRef, actRef, labelRef]) {
        const cv = ref.current!;
        if (cv.width !== pw || cv.height !== ph) {
          cv.width = pw; cv.height = ph;
          restDirty = true; // 视口尺寸变化，缓存失效
        }
      }

      // 防抖重渲染：相机静止 200ms 后按新精度重绘静息层
      if (restDirty && nowMs - camMovedAt > 200) {
        renderRest(pw, ph, w, h, dpr, now);
        restDirty = false;
      }

      const actCtx = actRef.current!.getContext("2d")!;
      const labelCtx = labelRef.current!.getContext("2d")!;
      const restCtx = restRef.current!.getContext("2d")!;

      // 世界变换：dpr * scale，平移到相机
      const tx = w / 2 - camera.x * camera.scale;
      const ty = h / 2 - camera.y * camera.scale;
      const setWorld = (ctx: CanvasRenderingContext2D) =>
        ctx.setTransform(dpr * camera.scale, 0, 0, dpr * camera.scale,
          dpr * tx, dpr * ty);

      restCtx.setTransform(1, 0, 0, 1, 0, 0);
      restCtx.fillStyle = THEME.colors.background;
      restCtx.fillRect(0, 0, pw, ph);
      if (!restDirty) {
        // 缓存与当前相机一致：1:1 贴图（清晰）
        restCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
        restCtx.drawImage(off, 0, 0);
      } else {
        // 交互中：按相机差量变换贴图（暂时模糊，松手后自动恢复）
        const a = camera.scale / offCam.scale;
        const e = w / 2 + (offCam.x - camera.x) * camera.scale - (w / 2) * a;
        const f = h / 2 + (offCam.y - camera.y) * camera.scale - (h / 2) * a;
        restCtx.setTransform(dpr * a, 0, 0, dpr * a, dpr * e, dpr * f);
        if (off.width > 0) restCtx.drawImage(off, 0, 0);
      }

      actCtx.clearRect(0, 0, pw, ph);
      setWorld(actCtx);
      actCtx.lineWidth = 1 / camera.scale;
      drawActivationLayer(actCtx, scene, engine, now);

      labelCtx.clearRect(0, 0, pw, ph);
      setWorld(labelCtx);
      drawLabelLayer(labelCtx, scene, engine, camera, hoverRef.current);

      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);

    // 交互
    const labelCv = labelRef.current!;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = labelCv.getBoundingClientRect();
      // 以视口中心为锚缩放（2026-08-08 用户决议：鼠标锚点缩放会感觉图谱“跳走”，违背直觉）
      camera.zoomAt(rect.width / 2, rect.height / 2,
        rect.width, rect.height, e.deltaY < 0 ? 1.12 : 1 / 1.12);
    };
    const onDown = (e: PointerEvent) => {
      dragRef.current = { x: e.clientX, y: e.clientY, moved: false };
      labelCv.setPointerCapture(e.pointerId);
    };
    const onMove = (e: PointerEvent) => {
      const rect = labelCv.getBoundingClientRect();
      const d = dragRef.current;
      if (d) {
        const dx = e.clientX - d.x, dy = e.clientY - d.y;
        if (Math.abs(dx) + Math.abs(dy) > 3) d.moved = true;
        camera.panBy(dx, dy);
        d.x = e.clientX; d.y = e.clientY;
      } else {
        const [wx, wy] = camera.toWorld(e.clientX - rect.left, e.clientY - rect.top,
          rect.width, rect.height);
        hoverRef.current = nearestNode(data.nodes, wx, wy, 12 / camera.scale)?.id ?? null;
        labelCv.style.cursor = hoverRef.current ? "pointer" : "default";
      }
    };
    const onUp = () => {
      const d = dragRef.current;
      dragRef.current = null;
      if (d && !d.moved && hoverRef.current) onNodeClick(hoverRef.current);
    };
    labelCv.addEventListener("wheel", onWheel, { passive: false });
    labelCv.addEventListener("pointerdown", onDown);
    labelCv.addEventListener("pointermove", onMove);
    labelCv.addEventListener("pointerup", onUp);

    return () => {
      cancelAnimationFrame(raf);
      labelCv.removeEventListener("wheel", onWheel);
      labelCv.removeEventListener("pointerdown", onDown);
      labelCv.removeEventListener("pointermove", onMove);
      labelCv.removeEventListener("pointerup", onUp);
    };
  }, [data, engine, onNodeClick]);

  return (
    <div className="relative h-full w-full overflow-hidden">
      <canvas ref={restRef} className="absolute inset-0 h-full w-full" />
      <canvas ref={actRef} className="absolute inset-0 h-full w-full" />
      <canvas ref={labelRef} className="absolute inset-0 h-full w-full" />
    </div>
  );
}

function nearestNode(
  nodes: GraphNode[], wx: number, wy: number, radius: number
): GraphNode | null {
  let best: GraphNode | null = null;
  let bestD = radius;
  for (const nd of nodes) {
    const d = Math.hypot(nd.x - wx, nd.y - wy);
    if (d < bestD) { bestD = d; best = nd; }
  }
  return best;
}
