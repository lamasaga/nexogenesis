import asyncio

from nexogenesis.runtime.events import EventBus
from nexogenesis.runtime.graph_data import build_graph_payload
from nexogenesis.runtime.simulate import (
    SCENARIO_NAMES, build_scenario, run_scenario,
)


def test_scenario_names():
    assert set(SCENARIO_NAMES) == {"judge", "talk", "digest"}


def test_judge_scenario_sequence(kb_root):
    graph = build_graph_payload(kb_root)
    events = build_scenario("judge", graph)
    types = [t for _, t, _ in events]
    assert types[0] == "skill.trigger"
    assert types[1] == "retrieve.query"
    assert "graph.hit" in types
    assert types.count("lens.begin") == 3
    assert types[-1] == "session.idle"
    # 时间单调不减
    times = [t for t, _, _ in events]
    assert times == sorted(times)


def test_judge_conflict_role_present(kb_root):
    graph = build_graph_payload(kb_root)
    events = build_scenario("judge", graph)
    hits = [p for _, t, p in events if t == "graph.hit"]
    roles = {h["role"] for h in hits}
    assert "seed" in roles and "expand" in roles and "conflict" in roles


def test_unknown_scenario_raises(kb_root):
    graph = build_graph_payload(kb_root)
    try:
        build_scenario("nonexistent", graph)
        assert False, "应抛 KeyError"
    except KeyError:
        pass


def test_run_scenario_publishes_in_order(kb_root):
    graph = build_graph_payload(kb_root)
    events = [(0.0, t, p) for _, t, p in build_scenario("talk", graph)]

    async def go():
        bus = EventBus()
        q = bus.subscribe()
        await run_scenario(bus, events)
        got = []
        while not q.empty():
            got.append(q.get_nowait().type)
        return got

    got = asyncio.run(go())
    assert got == [t for _, t, _ in events]


def test_runner_batch_mode(kb_root):
    """batch=True：忽略时刻表，以固定间隔连发，顺序与数量不变。"""
    graph = build_graph_payload(kb_root)

    async def go():
        from nexogenesis.runtime.simulate import SimulationRunner

        bus = EventBus()
        q = bus.subscribe()
        runner = SimulationRunner(bus, lambda: graph)
        await runner.submit("digest", batch=True)
        await asyncio.sleep(3.0)  # digest 5 个事件 × 0.3s 间隔
        got = []
        while not q.empty():
            got.append(q.get_nowait().type)
        return got

    got = asyncio.run(go())
    assert len(got) == 5
    assert got[0] == "skill.trigger"
    assert got[-1] == "session.idle"
