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

    // 静息层：离屏渲染一次（世界坐标，2x 超采样）
    const off = document.createElement("canvas");
    const pad = 200;
    const xs = data.nodes.map((n) => n.x);
    const ys = data.nodes.map((n) => n.y);
    const minX = Math.min(...xs) - pad, maxX = Math.max(...xs) + pad;
    const minY = Math.min(...ys) - pad, maxY = Math.max(...ys) + pad;
    const SS = 2;
    off.width = Math.max(1, (maxX - minX) * SS);
    off.height = Math.max(1, (maxY - minY) * SS);
    const offCtx = off.getContext("2d")!;
    offCtx.setTransform(SS, 0, 0, SS, -minX * SS, -minY * SS);
    drawRestLayer(offCtx, scene, (performance.now() - t0) / 1000);

    // 初始取景：整图居中
    const host = restRef.current!.parentElement!;
    const fit = () => {
      const w = host.clientWidth, h = host.clientHeight;
      camera.scale = Math.min(4, Math.max(0.2,
        Math.min(w / (maxX - minX), h / (maxY - minY)) * 0.95));
      camera.x = (minX + maxX) / 2;
      camera.y = (minY + maxY) / 2;
    };
    fit();

    const frame = (nowMs: number) => {
      const now = (nowMs - t0) / 1000;
      const dt = Math.min(0.1, (nowMs - last) / 1000);
      last = nowMs;
      engine.decay(dt);

      const w = host.clientWidth, h = host.clientHeight;
      const dpr = window.devicePixelRatio || 1;
      for (const ref of [restRef, actRef, labelRef]) {
        const cv = ref.current!;
        if (cv.width !== w * dpr || cv.height !== h * dpr) {
          cv.width = w * dpr; cv.height = h * dpr;
        }
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
      restCtx.fillRect(0, 0, w * dpr, h * dpr);
      setWorld(restCtx);
      restCtx.drawImage(off, minX, minY, maxX - minX, maxY - minY);

      actCtx.clearRect(0, 0, w * dpr, h * dpr);
      setWorld(actCtx);
      actCtx.lineWidth = 1 / camera.scale;
      drawActivationLayer(actCtx, scene, engine, now);

      labelCtx.clearRect(0, 0, w * dpr, h * dpr);
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
      camera.zoomAt(e.clientX - rect.left, e.clientY - rect.top,
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
