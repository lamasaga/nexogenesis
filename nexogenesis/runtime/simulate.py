from __future__ import annotations

SCENARIO_NAMES: list[str] = []


class SimulationRunner:
    """Task 6 填充完整实现。"""

    def __init__(self, bus, graph_fn) -> None:
        self.bus = bus
        self.graph_fn = graph_fn

    async def submit(self, name: str) -> int:
        raise NotImplementedError
