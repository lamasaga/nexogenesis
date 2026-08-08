from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field


@dataclass
class Event:
    type: str
    payload: dict
    ts: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps(
            {"type": self.type, "ts": self.ts, "payload": self.payload},
            ensure_ascii=False,
        )


class EventBus:
    """进程内 pub/sub；订阅者是 asyncio.Queue，SSE 端点逐条转发。"""

    def __init__(self) -> None:
        self._subs: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subs.discard(q)

    async def publish(self, type_: str, payload: dict) -> Event:
        ev = Event(type=type_, payload=payload)
        for q in list(self._subs):
            try:
                q.put_nowait(ev)
            except asyncio.QueueFull:
                pass  # 慢消费者丢帧，不阻塞发布者
        return ev
