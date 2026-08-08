import type { GraphData, SimEvent } from "../graph/types";

export async function fetchGraph(): Promise<GraphData> {
  const r = await fetch("/api/graph");
  if (!r.ok) throw new Error(`/api/graph ${r.status}`);
  return r.json();
}

export interface CardDetail {
  id: string; title: string; type: string; maturity: string;
  domains: string[]; updated: string; body: string;
}

export async function fetchCard(id: string): Promise<CardDetail> {
  const r = await fetch(`/api/cards/${encodeURIComponent(id)}`);
  if (!r.ok) throw new Error(`卡片不存在: ${id}`);
  return r.json();
}

export async function simulate(scenario: string, batch = false): Promise<void> {
  const r = await fetch(
    `/api/simulate/${encodeURIComponent(scenario)}${batch ? "?batch=1" : ""}`,
    { method: "POST" }
  );
  if (!r.ok) throw new Error(`未知剧本: ${scenario}`);
}

export interface ReplayEvent {
  t: number;
  type: string;
  payload: Record<string, unknown>;
}

export async function fetchReplay(scenario: string): Promise<ReplayEvent[]> {
  const r = await fetch(`/api/replay/${encodeURIComponent(scenario)}`);
  if (!r.ok) throw new Error(`未知剧本: ${scenario}`);
  return (await r.json()).events;
}

export function subscribeEvents(onEvent: (ev: SimEvent) => void): () => void {
  const es = new EventSource("/api/events");
  es.onmessage = (msg) => {
    try {
      onEvent(JSON.parse(msg.data) as SimEvent);
    } catch {
      /* 忽略坏帧 */
    }
  };
  return () => es.close();
}
