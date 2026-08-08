import { useEffect, useMemo, useRef, useState } from "react";
import { ActivationEngine } from "./activation/engine";
import { fetchGraph, fetchReplay, simulate, subscribeEvents } from "./api/client";
import { CardReader } from "./components/CardReader";
import { ChatPanel } from "./components/ChatPanel";
import { EventLog } from "./components/EventLog";
import { GraphCanvas } from "./graph/GraphCanvas";
import type { GraphData, SimEvent } from "./graph/types";

export default function App() {
  const [data, setData] = useState<GraphData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [events, setEvents] = useState<SimEvent[]>([]);
  const [cardId, setCardId] = useState<string | null>(null);
  const [, setTick] = useState(0);
  const t0Ref = useRef(performance.now() / 1000);

  useEffect(() => {
    fetchGraph().then(setData).catch((e) => setError(String(e)));
  }, []);

  const engine = useMemo(
    () => (data ? new ActivationEngine(new Map(data.edges.map((e) => [e.id, e.bundle]))) : null),
    [data]
  );

  useEffect(() => {
    if (!engine) return;
    // 截图走查模式（replay）不挂 SSE：常驻挂起的 EventSource 会冻结 headless 虚拟时钟
    if (new URLSearchParams(window.location.search).get("nosse") === "1") return;
    return subscribeEvents((ev: SimEvent) => {
      engine.handleEvent(ev, performance.now() / 1000 - t0Ref.current);
      setEvents((list) => [...list.slice(-99), ev]);
      setTick((n) => n + 1);
    });
  }, [engine]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const autoplay = params.get("autoplay");
    if (!autoplay || !engine) return;
    if (params.get("replay") === "1") {
      // 截图走查：一次性取剧本事件表，本地按 0.35x 压缩调度（不经 SSE）
      let cancelled = false;
      const timers: ReturnType<typeof setTimeout>[] = [];
      fetchReplay(autoplay).then((events) => {
        if (cancelled) return;
        for (const ev of events) {
          timers.push(setTimeout(() => {
            const now = performance.now() / 1000 - t0Ref.current;
            engine.handleEvent({ type: ev.type, ts: ev.t, payload: ev.payload }, now);
            setEvents((list) => [...list.slice(-99), { type: ev.type, ts: ev.t, payload: ev.payload }]);
            setTick((n) => n + 1);
          }, 1500 + ev.t * 350));
        }
      });
      return () => { cancelled = true; timers.forEach(clearTimeout); };
    }
    const batch = params.get("batch") === "1";
    const timer = setTimeout(() => simulate(autoplay, batch), 1500);
    return () => clearTimeout(timer);
  }, [engine]);

  if (error) return <div className="p-8 text-red-400">加载失败：{error}</div>;
  if (!data || !engine) return <div className="p-8 text-zinc-500">加载中…</div>;
  if (data.nodes.length === 0)
    return <div className="p-8 text-zinc-500">知识库为空：01-Cards/ 中没有卡片。</div>;

  return (
    <div className="flex h-full w-full flex-col">
      {/* 顶栏 */}
      <header className="flex h-11 shrink-0 items-center gap-3 border-b border-white/[0.06] px-4">
        <span className="flex items-center gap-2 text-[13px] font-medium text-zinc-200">
          <span className="inline-block h-2 w-2 rounded-full bg-teal-400 shadow-[0_0_8px_rgba(45,212,191,0.8)]" />
          Nexogenesis
        </span>
        {engine.skillLabel && (
          <span className="flex items-center gap-1.5 rounded-full border border-teal-400/25 bg-teal-400/10 px-2.5 py-0.5 text-[11px] text-teal-300">
            <span className="inline-block h-1 w-1 animate-pulse rounded-full bg-teal-300" />
            {engine.skillLabel}
          </span>
        )}
        {engine.lensLabel && (
          <span className="rounded-full border border-amber-400/25 bg-amber-400/10 px-2.5 py-0.5 text-[11px] text-amber-300">
            {engine.lensLabel}
          </span>
        )}
        <span className="ml-auto text-[11px] text-zinc-600">
          {data.nodes.length} 节点 · {data.edges.length} 边
        </span>
      </header>

      {/* 主区 */}
      <div className="flex min-h-0 flex-1">
        <div className="graph-vignette relative min-w-0 flex-1">
          <GraphCanvas data={data} engine={engine} onNodeClick={setCardId} />
        </div>
        <aside className="flex w-80 shrink-0 flex-col border-l border-white/[0.06]">
          <div className="min-h-0 flex-1">
            <ChatPanel onTrigger={simulate} />
          </div>
          <div className="h-52 shrink-0 border-t border-white/[0.06]">
            <div className="micro-label px-3 pt-2">事件流</div>
            <EventLog events={events} />
          </div>
        </aside>
      </div>

      <CardReader cardId={cardId} onClose={() => setCardId(null)} />
    </div>
  );
}
