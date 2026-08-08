import type { SimEvent } from "../graph/types";

const TYPE_COLORS: Record<string, string> = {
  "skill.trigger": "text-teal-300",
  "retrieve.query": "text-amber-200",
  "graph.hit": "text-sky-300",
  "lens.begin": "text-amber-400",
  "card.read": "text-emerald-300",
  "write.applied": "text-fuchsia-300",
  "session.idle": "text-slate-500",
};

export function EventLog({ events }: { events: SimEvent[] }) {
  return (
    <div className="flex h-full flex-col overflow-hidden rounded-lg border border-slate-700/60 bg-slate-950/80">
      <div className="border-b border-slate-700/60 px-3 py-1.5 text-xs text-slate-400">
        事件流
      </div>
      <div className="flex-1 overflow-y-auto px-3 py-1 font-mono text-[11px] leading-5">
        {events.slice(-60).map((ev, i) => (
          <div key={i} className={TYPE_COLORS[ev.type] ?? "text-slate-400"}>
            › {ev.type} {summarize(ev)}
          </div>
        ))}
      </div>
    </div>
  );
}

function summarize(ev: SimEvent): string {
  const p = ev.payload as Record<string, unknown>;
  if (ev.type === "graph.hit") return `${p.role} nodes=${(p.node_ids as string[]).length}`;
  if (ev.type === "lens.begin") return `${p.name}`;
  if (ev.type === "skill.trigger") return `${p.skill}`;
  if (ev.type === "retrieve.query") return `${p.mode}`;
  if (ev.type === "card.read") return `${p.card_id}`;
  return "";
}
