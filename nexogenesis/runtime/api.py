from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from nexogenesis.runtime.events import EventBus
from nexogenesis.runtime.graph_data import build_graph_payload
from nexogenesis.runtime.layout import ensure_layout
from nexogenesis.runtime.simulate import SimulationRunner, SCENARIO_NAMES
from nexogenesis.store import Store


def create_app(root: Path) -> FastAPI:
    root = root.resolve()
    app = FastAPI(title="Nexogenesis Runtime")
    bus = EventBus()
    runner = SimulationRunner(bus, lambda: build_graph_payload(root))

    @app.get("/api/graph")
    def get_graph() -> dict:
        payload = build_graph_payload(root)
        pos = ensure_layout(root, payload["nodes"])
        for n in payload["nodes"]:
            n["x"] = pos[n["id"]]["x"]
            n["y"] = pos[n["id"]]["y"]
        return payload

    @app.get("/api/graph/stats")
    def get_stats() -> dict:
        payload = build_graph_payload(root)
        by_type: dict[str, int] = {}
        for n in payload["nodes"]:
            by_type[n["type"]] = by_type.get(n["type"], 0) + 1
        return {
            "node_count": len(payload["nodes"]),
            "edge_count": len(payload["edges"]),
            "nodes_by_type": by_type,
        }

    @app.get("/api/cards/{card_id}")
    def get_card(card_id: str) -> dict:
        store = Store(root / "01-Cards").load()
        card = store.cards.get(card_id)
        if card is None:
            raise HTTPException(status_code=404, detail=f"卡片不存在: {card_id}")
        return {
            "id": card.id,
            "title": card.title,
            "type": card.type.value,
            "maturity": card.maturity.value,
            "domains": card.domains,
            "updated": card.updated,
            "body": card.body,
        }

    app.include_router(_events_router(bus))
    app.include_router(_simulate_router(runner, lambda: build_graph_payload(root)))

    dist = root / "web" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")
    return app


def _events_router(bus: EventBus):
    from fastapi import APIRouter
    from fastapi.responses import StreamingResponse

    router = APIRouter()

    @router.get("/api/events")
    async def events() -> StreamingResponse:
        queue = bus.subscribe()

        async def stream():
            try:
                yield "retry: 2000\n\n"
                while True:
                    ev = await queue.get()
                    yield f"data: {ev.to_json()}\n\n"
            finally:
                bus.unsubscribe(queue)

        return StreamingResponse(stream(), media_type="text/event-stream")

    return router


def _simulate_router(runner: SimulationRunner, graph_fn):
    from fastapi import APIRouter

    from nexogenesis.runtime.simulate import build_scenario

    router = APIRouter()

    @router.post("/api/simulate/{scenario}")
    async def simulate(scenario: str, batch: bool = False) -> dict:
        if scenario not in SCENARIO_NAMES:
            raise HTTPException(status_code=404,
                                detail=f"未知剧本: {scenario}，可选 {SCENARIO_NAMES}")
        position = await runner.submit(scenario, batch=batch)
        return {"queued": position, "scenario": scenario, "batch": batch}

    @router.get("/api/replay/{scenario}")
    def replay(scenario: str) -> dict:
        """一次性返回剧本事件表（截图走查用：前端本地调度，不经 SSE 实时流）。"""
        if scenario not in SCENARIO_NAMES:
            raise HTTPException(status_code=404,
                                detail=f"未知剧本: {scenario}，可选 {SCENARIO_NAMES}")
        events = build_scenario(scenario, graph_fn())
        return {"events": [{"t": t, "type": ty, "payload": p}
                           for t, ty, p in events]}

    return router
