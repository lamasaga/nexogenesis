import asyncio
import json

from nexogenesis.runtime.events import Event, EventBus


def test_event_json_envelope():
    ev = Event(type="graph.hit", payload={"node_ids": ["a"], "role": "seed"})
    data = json.loads(ev.to_json())
    assert data["type"] == "graph.hit"
    assert data["payload"]["role"] == "seed"
    assert data["ts"] > 0


def test_bus_fanout():
    async def go():
        bus = EventBus()
        q1, q2 = bus.subscribe(), bus.subscribe()
        await bus.publish("skill.trigger", {"skill": "nexo-judge"})
        for q in (q1, q2):
            ev = await asyncio.wait_for(q.get(), timeout=1)
            assert ev.type == "skill.trigger"
        bus.unsubscribe(q1)
        await bus.publish("session.idle", {})
        async with asyncio.timeout(0.2):
            ev = await q2.get()
            assert ev.type == "session.idle"
        assert q1.empty()

    asyncio.run(go())


def test_event_chinese_payload():
    ev = Event(type="retrieve.query", payload={"query": "深判：止损"})
    assert "深判" in ev.to_json()
