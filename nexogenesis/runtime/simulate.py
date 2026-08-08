from __future__ import annotations

import asyncio
from typing import Callable

from nexogenesis.runtime.events import EventBus

SCENARIO_NAMES = ["judge", "talk", "digest"]

TimedEvent = tuple[float, str, dict]


def _seed_nodes(graph: dict, n: int) -> list[str]:
    """优先取 claim/model 卡作为种子，不足时用任意卡补足。"""
    preferred = [nd["id"] for nd in graph["nodes"]
                 if nd["type"] in ("claim", "model", "conflict")]
    pool = preferred or [nd["id"] for nd in graph["nodes"]]
    return pool[:n]


def _edges_touching(graph: dict, node_ids: set[str], cap: int) -> list[dict]:
    out = [e for e in graph["edges"]
           if e["from"] in node_ids or e["to"] in node_ids]
    return out[:cap]


def _conflict_edges(graph: dict) -> list[dict]:
    return [e for e in graph["edges"]
            if e.get("relation_type") == "conflicts-with"]


def build_judge(graph: dict) -> list[TimedEvent]:
    seeds = _seed_nodes(graph, 2)
    expand = _edges_touching(graph, set(seeds), cap=9)
    conflict = _conflict_edges(graph)
    others = [nd["id"] for nd in graph["nodes"] if nd["id"] not in seeds]
    lens_names = ["证据强度", "适用边界", "反事实"]
    events: list[TimedEvent] = [
        (0.2, "skill.trigger", {"skill": "nexo-judge"}),
        (1.2, "retrieve.query", {"mode": "judge", "query": "深判（模拟）"}),
        (2.4, "graph.hit", {"node_ids": seeds, "edge_ids": [], "role": "seed"}),
        (3.8, "graph.hit", {
            "node_ids": sorted({e["to"] for e in expand} | {e["from"] for e in expand}),
            "edge_ids": [e["id"] for e in expand],
            "role": "expand",
        }),
    ]
    if conflict:
        events.append((6.4, "graph.hit", {
            "node_ids": sorted({e["to"] for e in conflict} | {e["from"] for e in conflict}),
            "edge_ids": [e["id"] for e in conflict],
            "role": "conflict",
        }))
    t = 9.0
    for i, name in enumerate(lens_names):
        pick = others[i:i + 2] or seeds
        near = _edges_touching(graph, set(pick), cap=3)
        events.append((t, "lens.begin", {
            "index": i + 1, "name": name,
            "node_ids": pick, "edge_ids": [e["id"] for e in near],
        }))
        t += 3.6
    events.append((t + 0.5, "session.idle", {"reason": "judge-complete"}))
    return events


def build_talk(graph: dict) -> list[TimedEvent]:
    seeds = _seed_nodes(graph, 1)
    expand = _edges_touching(graph, set(seeds), cap=6)
    reads = [nd["id"] for nd in graph["nodes"]
             if nd["id"] not in seeds][:2]
    events: list[TimedEvent] = [
        (0.2, "skill.trigger", {"skill": "nexo-talk"}),
        (0.8, "retrieve.query", {"mode": "talk", "query": "问答（模拟）"}),
        (1.8, "graph.hit", {"node_ids": seeds, "edge_ids": [], "role": "seed"}),
        (2.8, "graph.hit", {
            "node_ids": sorted({e["to"] for e in expand} | {e["from"] for e in expand}),
            "edge_ids": [e["id"] for e in expand],
            "role": "expand",
        }),
    ]
    t = 4.5
    for cid in reads:
        events.append((t, "card.read", {"card_id": cid}))
        t += 1.5
    events.append((t + 1.0, "session.idle", {"reason": "talk-complete"}))
    return events


def build_digest(graph: dict) -> list[TimedEvent]:
    seeds = _seed_nodes(graph, 1)
    events: list[TimedEvent] = [
        (0.2, "skill.trigger", {"skill": "nexo-digest"}),
        (0.8, "retrieve.query", {"mode": "digest", "query": "消化（模拟）"}),
        (2.0, "graph.hit", {"node_ids": seeds, "edge_ids": [], "role": "seed"}),
        (3.5, "write.applied", {"created": [], "enriched": seeds}),
        (6.0, "session.idle", {"reason": "digest-complete"}),
    ]
    return events


_BUILDERS: dict[str, Callable[[dict], list[TimedEvent]]] = {
    "judge": build_judge,
    "talk": build_talk,
    "digest": build_digest,
}


def build_scenario(name: str, graph: dict) -> list[TimedEvent]:
    return _BUILDERS[name](graph)


async def run_scenario(bus: EventBus, events: list[TimedEvent],
                       batch_gap: float | None = None) -> None:
    """按剧本时刻表发布事件；batch_gap 非 None 时忽略时刻表、以固定间隔连发（截图走查用）。"""
    t0 = 0.0
    for t, type_, payload in events:
        if batch_gap is None:
            await asyncio.sleep(max(0.0, t - t0))
            t0 = t
        else:
            await asyncio.sleep(batch_gap)
        await bus.publish(type_, payload)


class SimulationRunner:
    """串行执行：同一时刻只演一场，其余排队。"""

    def __init__(self, bus: EventBus, graph_fn: Callable[[], dict]) -> None:
        self.bus = bus
        self.graph_fn = graph_fn
        self._queue: asyncio.Queue | None = None

    async def submit(self, name: str, batch: bool = False) -> int:
        if name not in _BUILDERS:
            raise KeyError(name)
        if self._queue is None:
            self._queue = asyncio.Queue()
            asyncio.create_task(self._work())
        events = build_scenario(name, self.graph_fn())
        await self._queue.put((events, batch))
        return self._queue.qsize()

    async def _work(self) -> None:
        while True:
            events, batch = await self._queue.get()
            await run_scenario(self.bus, events,
                               batch_gap=0.3 if batch else None)
