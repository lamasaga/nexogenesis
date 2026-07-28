"""短期记忆：跨会话卷（默认最多 10）+ 当前热槽。"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from nexogenesis.thinking.config import get_nested, load_attention_config
from nexogenesis.yaml_utils import atomic_write_file

EMPTY_SLOTS: dict[str, Any] = {
    "focus": "",
    "claims_user": [],
    "claims_system": [],
    "tensions": [],
    "cited_cards": [],
    "rag_footprints": [],
    "user_directives": [],
    "bridge_hints": [],
    "turn": 0,
    "capture_prompts": 0,
    "last_signal_turn": -999,
    "signals_disabled_capture": False,
    "session_overrides": {},
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dump(path: Path, data: dict[str, Any]) -> None:
    atomic_write_file(
        path, yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    )


class STMStore:
    def __init__(self, root: Path, *, config: dict[str, Any] | None = None):
        self.root = root.resolve()
        self.config = config if config is not None else load_attention_config(self.root)
        rel = get_nested(self.config, "stm", "path", default=".nexogenesis/memory/stm")
        self.dir = self.root / str(rel)
        self.index_path = self.dir / "index.yaml"

    def ensure(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            _dump(
                self.index_path,
                {
                    "version": 1,
                    "current_session_id": None,
                    "sessions": [],
                    "fossils": [],
                },
            )

    def load_index(self) -> dict[str, Any]:
        self.ensure()
        data = yaml.safe_load(self.index_path.read_text(encoding="utf-8")) or {}
        data.setdefault("sessions", [])
        data.setdefault("fossils", [])
        data.setdefault("current_session_id", None)
        return data

    def save_index(self, index: dict[str, Any]) -> None:
        self.ensure()
        _dump(self.index_path, index)

    def _session_path(self, session_id: str) -> Path:
        safe = "".join(c for c in session_id if c.isalnum() or c in "-_")
        return self.dir / f"session-{safe}.yaml"

    def load_session(self, session_id: str) -> dict[str, Any] | None:
        path = self._session_path(session_id)
        if not path.exists():
            return None
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        slots = dict(EMPTY_SLOTS)
        slots.update(data.get("slots") or {})
        data["slots"] = slots
        return data

    def save_session(self, session: dict[str, Any]) -> None:
        sid = session["id"]
        _dump(self._session_path(sid), session)

    def max_sessions(self) -> int:
        return int(get_nested(self.config, "stm", "max_sessions", default=10))

    def overflow_mode(self) -> str:
        return str(get_nested(self.config, "stm", "overflow", default="drop"))

    def start_session(self, *, title: str = "") -> dict[str, Any]:
        index = self.load_index()
        # 若已有当前会话未结束，先封存
        if index.get("current_session_id"):
            self.end_session()
            index = self.load_index()

        sid = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:6]
        session = {
            "id": sid,
            "title": title or "untitled",
            "created": _now_iso(),
            "updated": _now_iso(),
            "status": "open",
            "slots": dict(EMPTY_SLOTS),
        }
        self.save_session(session)
        index["sessions"].append(
            {
                "id": sid,
                "title": session["title"],
                "created": session["created"],
                "status": "open",
            }
        )
        index["current_session_id"] = sid
        self.save_index(index)
        self._enforce_capacity()
        return session

    def end_session(self) -> str | None:
        index = self.load_index()
        sid = index.get("current_session_id")
        if not sid:
            return None
        session = self.load_session(sid)
        if session:
            session["status"] = "closed"
            session["updated"] = _now_iso()
            self.save_session(session)
        for meta in index["sessions"]:
            if meta.get("id") == sid:
                meta["status"] = "closed"
        index["current_session_id"] = None
        self.save_index(index)
        self._enforce_capacity()
        return sid

    def current_session(self) -> dict[str, Any] | None:
        index = self.load_index()
        sid = index.get("current_session_id")
        if not sid:
            return None
        return self.load_session(sid)

    def require_current(self) -> dict[str, Any]:
        cur = self.current_session()
        if cur:
            return cur
        return self.start_session(title="auto")

    def update_slots(
        self,
        *,
        focus: str | None = None,
        add_claim_user: str | None = None,
        add_claim_system: str | None = None,
        add_tension: str | None = None,
        cite: list[str] | None = None,
        add_rag_footprint: str | None = None,
        add_directive: str | None = None,
        add_bridge_hint: str | None = None,
        bump_turn: bool = False,
        increment_capture_prompt: bool = False,
        mark_signal_turn: bool = False,
        disable_capture_prompts: bool | None = None,
        session_overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session = self.require_current()
        slots = session["slots"]

        if focus is not None:
            slots["focus"] = focus
        if add_claim_user:
            slots["claims_user"] = _uniq_append(slots.get("claims_user") or [], add_claim_user)
        if add_claim_system:
            slots["claims_system"] = _uniq_append(
                slots.get("claims_system") or [], add_claim_system
            )
        if add_tension:
            slots["tensions"] = _uniq_append(slots.get("tensions") or [], add_tension)
        if cite:
            cards = list(slots.get("cited_cards") or [])
            for c in cite:
                if c and c not in cards:
                    cards.append(c)
            slots["cited_cards"] = cards
        if add_rag_footprint:
            slots["rag_footprints"] = _uniq_append(
                slots.get("rag_footprints") or [], add_rag_footprint
            )
        if add_directive:
            slots["user_directives"] = _uniq_append(
                slots.get("user_directives") or [], add_directive
            )
            if any(k in add_directive for k in ("先别记", "别记", "不要捕获", "别捕获")):
                slots["signals_disabled_capture"] = True
        if add_bridge_hint:
            slots["bridge_hints"] = _uniq_append(
                slots.get("bridge_hints") or [], add_bridge_hint
            )
        if bump_turn:
            slots["turn"] = int(slots.get("turn") or 0) + 1
        if increment_capture_prompt:
            slots["capture_prompts"] = int(slots.get("capture_prompts") or 0) + 1
        if mark_signal_turn:
            slots["last_signal_turn"] = int(slots.get("turn") or 0)
        if disable_capture_prompts is not None:
            slots["signals_disabled_capture"] = bool(disable_capture_prompts)
        if session_overrides is not None:
            slots["session_overrides"] = session_overrides

        session["slots"] = slots
        session["updated"] = _now_iso()
        self.save_session(session)
        return session

    def set_session_overrides(self, overrides: dict[str, Any]) -> dict[str, Any]:
        return self.update_slots(session_overrides=overrides)

    def clear_session_overrides(self) -> dict[str, Any]:
        return self.update_slots(session_overrides={})

    def get_session_overrides(self) -> dict[str, Any]:
        cur = self.current_session()
        if not cur:
            return {}
        return dict((cur.get("slots") or {}).get("session_overrides") or {})

    def attention_context(self) -> dict[str, Any]:
        """供组装：当前卷 + 最近已封存卷的焦点/张力/引用摘要。"""
        index = self.load_index()
        current = self.current_session()
        recent: list[dict[str, Any]] = []
        for meta in reversed(index.get("sessions") or []):
            sid = meta.get("id")
            if not sid or (current and sid == current["id"]):
                continue
            sess = self.load_session(sid)
            if not sess:
                continue
            sl = sess.get("slots") or {}
            recent.append({
                "id": sid,
                "title": sess.get("title"),
                "focus": sl.get("focus") or "",
                "tensions": (sl.get("tensions") or [])[:5],
                "cited_cards": (sl.get("cited_cards") or [])[:8],
            })
            if len(recent) >= self.max_sessions():
                break

        slots = (current or {}).get("slots") or dict(EMPTY_SLOTS)
        return {
            "current_session_id": (current or {}).get("id"),
            "slots": slots,
            "recent_sessions": recent,
            "all_cited": _collect_cited(slots, recent),
            "all_tensions": _collect_tensions(slots, recent),
            "focus_tokens": _focus_blob(slots, recent),
        }

    def _enforce_capacity(self) -> None:
        index = self.load_index()
        sessions = list(index.get("sessions") or [])
        max_n = self.max_sessions()
        # 当前 open 会话不计入「可删」优先；总文件数仍受限
        while len(sessions) > max_n:
            oldest = sessions[0]
            oid = oldest.get("id")
            if oid and index.get("current_session_id") == oid:
                # 不应删除当前；若只有当前超限则 break
                if len(sessions) == 1:
                    break
                # 找下一个 closed
                closed_idx = next(
                    (i for i, s in enumerate(sessions) if s.get("status") != "open"),
                    None,
                )
                if closed_idx is None:
                    break
                oldest = sessions.pop(closed_idx)
                oid = oldest.get("id")
            else:
                sessions.pop(0)

            if oid:
                if self.overflow_mode() == "fossil":
                    fossils = index.setdefault("fossils", [])
                    fossils.append({
                        "id": oid,
                        "title": oldest.get("title"),
                        "created": oldest.get("created"),
                    })
                    fossils[:] = fossils[-20:]
                path = self._session_path(oid)
                if path.exists():
                    path.unlink()

        index["sessions"] = sessions
        self.save_index(index)


def _uniq_append(items: list, value: str, *, limit: int = 40) -> list:
    v = value.strip()
    if not v:
        return items
    out = list(items)
    if v not in out:
        out.append(v)
    return out[-limit:]


def _collect_cited(slots: dict, recent: list[dict]) -> list[str]:
    out: list[str] = []
    for c in slots.get("cited_cards") or []:
        if c not in out:
            out.append(c)
    for r in recent:
        for c in r.get("cited_cards") or []:
            if c not in out:
                out.append(c)
    return out


def _collect_tensions(slots: dict, recent: list[dict]) -> list[str]:
    out: list[str] = []
    for t in slots.get("tensions") or []:
        if t not in out:
            out.append(t)
    for r in recent:
        for t in r.get("tensions") or []:
            if t not in out:
                out.append(t)
    return out[:20]


def _focus_blob(slots: dict, recent: list[dict]) -> str:
    parts = [slots.get("focus") or ""]
    parts.extend(slots.get("bridge_hints") or [])
    for r in recent[:3]:
        if r.get("focus"):
            parts.append(r["focus"])
    return " ".join(p for p in parts if p)
