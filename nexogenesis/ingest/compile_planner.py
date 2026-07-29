"""Compile 分波调度：按 Inbox 库存选择本波文档与载荷策略。"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from nexogenesis.ingest.batch_runner import build_batches, max_docs_for_genre
from nexogenesis.ingest.chunker import build_compile_units


DEFAULT_MAX_CHARS = 10000
DEEP_MAX_CHARS = 8000
DEFAULT_WAVE_PROMPTS = 4
DEFAULT_WAVE_DOCS = 5

GENRE_PRIORITY = {
    "scrap": 0,
    "dialogue": 1,
    "essay": 2,
    "paper": 3,
    "generic": 4,
    "book": 5,
}

PROGRESS_NAME = "progress.json"
MANIFEST_NAME = "wave-manifest.json"


@dataclass
class CompilePolicy:
    max_chars: int = DEFAULT_MAX_CHARS
    wave_prompts: int = DEFAULT_WAVE_PROMPTS
    wave_docs: int = DEFAULT_WAVE_DOCS
    deep: bool = False
    process_all: bool = False


@dataclass(frozen=True)
class InventoryItem:
    path: Path
    doc_type: str
    genre: str
    char_count: int
    name: str = ""

    def __post_init__(self):
        if not self.name:
            object.__setattr__(self, "name", self.path.name)


@dataclass
class WavePlan:
    policy: CompilePolicy
    selected: list[InventoryItem]
    deferred: list[InventoryItem]
    units: list[dict] = field(default_factory=list)
    batches: list[list[dict]] = field(default_factory=list)
    remaining_inbox: int = 0


def resolve_policy(
    *,
    deep: bool = False,
    max_chars: int | None = None,
    wave_prompts: int | None = None,
    wave_docs: int | None = None,
    process_all: bool = False,
) -> CompilePolicy:
    if deep:
        default_chars = DEEP_MAX_CHARS
        default_prompts = 1
        default_docs = 1
    else:
        default_chars = DEFAULT_MAX_CHARS
        default_prompts = DEFAULT_WAVE_PROMPTS
        default_docs = DEFAULT_WAVE_DOCS

    return CompilePolicy(
        max_chars=max_chars if max_chars is not None else default_chars,
        wave_prompts=wave_prompts if wave_prompts is not None else default_prompts,
        wave_docs=wave_docs if wave_docs is not None else default_docs,
        deep=deep,
        process_all=process_all,
    )


def build_inventory(compile_plan: list[dict], genres: dict[str, str]) -> list[InventoryItem]:
    items = []
    for item in compile_plan:
        path: Path = item["path"]
        name = item.get("name") or path.name
        genre = (
            genres.get(name)
            or genres.get(path.name)
            or item["predicted_genre"]
        )
        meta = item.get("metadata") or {}
        items.append(
            InventoryItem(
                path=path,
                doc_type=item["doc_type"],
                genre=genre,
                char_count=int(meta.get("char_count") or 0),
                name=name,
            )
        )
    return items


def _sort_inventory(items: list[InventoryItem]) -> list[InventoryItem]:
    return sorted(
        items,
        key=lambda i: (GENRE_PRIORITY.get(i.genre, 99), i.char_count, i.name),
    )


def load_progress(tmp_dir: Path) -> dict:
    path = tmp_dir / PROGRESS_NAME
    if not path.exists():
        return {"sources": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"sources": {}}
    if not isinstance(data, dict):
        return {"sources": {}}
    if not isinstance(data.get("sources"), dict):
        data["sources"] = {}
    return data


def save_progress(tmp_dir: Path, progress: dict) -> None:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    (tmp_dir / PROGRESS_NAME).write_text(
        json.dumps(progress, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def completed_unit_ids(progress: dict, source_name: str) -> set[str]:
    entry = (progress.get("sources") or {}).get(source_name) or {}
    ids = entry.get("completed_unit_ids") or []
    return set(ids) if isinstance(ids, list) else set()


def mark_units_completed(progress: dict, source_name: str, unit_ids: list[str]) -> None:
    sources = progress.setdefault("sources", {})
    entry = sources.setdefault(source_name, {"completed_unit_ids": []})
    done = set(entry.get("completed_unit_ids") or [])
    done.update(unit_ids)
    entry["completed_unit_ids"] = sorted(done)


def clear_source_progress(progress: dict, source_name: str) -> None:
    sources = progress.get("sources") or {}
    sources.pop(source_name, None)


def filter_pending_units(units: list[dict], progress: dict) -> list[dict]:
    pending = []
    for u in units:
        name = u.get("source_key") or u["source_path"].name
        if u["unit_id"] not in completed_unit_ids(progress, name):
            pending.append(u)
    return pending


def _docs_from_items(items: list[InventoryItem]) -> list[dict]:
    return [
        {"path": i.path, "doc_type": i.doc_type, "name": i.name}
        for i in items
    ]


def _genres_from_items(items: list[InventoryItem]) -> dict[str, str]:
    return {i.name: i.genre for i in items}


def pack_units(units: list[dict], policy: CompilePolicy) -> list[list[dict]]:
    return build_batches(
        units,
        max_chars=policy.max_chars,
        group_by_genre=True,
        max_docs_per_batch_fn=max_docs_for_genre,
    )


def build_pending_batches(
    items: list[InventoryItem],
    policy: CompilePolicy,
    progress: dict,
) -> tuple[list[dict], list[list[dict]]]:
    if not items:
        return [], []
    units = build_compile_units(
        _docs_from_items(items),
        max_chars=policy.max_chars,
        genres=_genres_from_items(items),
    )
    pending = filter_pending_units(units, progress)
    return pending, pack_units(pending, policy)


def _units_from_batches(batches: list[list[dict]]) -> list[dict]:
    return [u for b in batches for u in b]


def _wave_from_capped(
    *,
    policy: CompilePolicy,
    selected: list[InventoryItem],
    deferred: list[InventoryItem],
    all_batches: list[list[dict]],
) -> WavePlan:
    capped = all_batches[: policy.wave_prompts]
    units = _units_from_batches(capped)
    remaining_names = {i.name for i in deferred}
    selected_unit_ids = {u["unit_id"] for u in units}
    for item in selected:
        pending_for_item = [
            u
            for b in all_batches
            for u in b
            if (u.get("source_key") or u["source_path"].name) == item.name
        ]
        if any(u["unit_id"] not in selected_unit_ids for u in pending_for_item):
            remaining_names.add(item.name)
    return WavePlan(
        policy=policy,
        selected=selected,
        deferred=deferred,
        units=units,
        batches=capped,
        remaining_inbox=len(remaining_names),
    )


def select_wave(
    inventory: list[InventoryItem],
    policy: CompilePolicy,
    progress: dict,
) -> WavePlan:
    ordered = _sort_inventory(inventory)

    if policy.process_all:
        active = []
        for item in ordered:
            _, batches = build_pending_batches([item], policy, progress)
            if batches:
                active.append(item)
        pending, batches = build_pending_batches(active, policy, progress)
        return WavePlan(
            policy=policy,
            selected=active,
            deferred=[],
            units=pending,
            batches=batches,
            remaining_inbox=0,
        )

    selected: list[InventoryItem] = []
    i = 0
    while i < len(ordered):
        item = ordered[i]
        _, solo_batches = build_pending_batches([item], policy, progress)
        if not solo_batches:
            i += 1
            continue

        if item.genre == "book" or policy.deep:
            if selected:
                return _wave_from_capped(
                    policy=policy,
                    selected=selected,
                    deferred=ordered[i:],
                    all_batches=build_pending_batches(selected, policy, progress)[1],
                )
            return _wave_from_capped(
                policy=policy,
                selected=[item],
                deferred=ordered[i + 1 :],
                all_batches=solo_batches,
            )

        candidate = selected + [item]
        if len(candidate) > policy.wave_docs:
            break

        _, batches = build_pending_batches(candidate, policy, progress)
        if len(batches) > policy.wave_prompts:
            if not selected:
                return _wave_from_capped(
                    policy=policy,
                    selected=[item],
                    deferred=ordered[i + 1 :],
                    all_batches=solo_batches,
                )
            break

        selected = candidate
        i += 1

    if not selected:
        for idx, item in enumerate(ordered):
            _, solo_batches = build_pending_batches([item], policy, progress)
            if solo_batches:
                return _wave_from_capped(
                    policy=policy,
                    selected=[item],
                    deferred=ordered[:idx] + ordered[idx + 1 :],
                    all_batches=solo_batches,
                )
        return WavePlan(policy=policy, selected=[], deferred=ordered, remaining_inbox=len(ordered))

    deferred = [x for x in ordered[i:] if x not in selected]
    # 也把循环中跳过的「已完成无 pending」文档算进 deferred 展示
    selected_set = set(selected)
    deferred = [x for x in ordered if x not in selected_set]
    _, batches = build_pending_batches(selected, policy, progress)
    return _wave_from_capped(
        policy=policy,
        selected=selected,
        deferred=deferred,
        all_batches=batches,
    )


def write_wave_manifest(
    tmp_dir: Path,
    wave: WavePlan,
    batch_files: list[str],
) -> Path:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    unit_ids_by_source: dict[str, list[str]] = {}
    for u in wave.units:
        key = u.get("source_key") or u["source_path"].name
        unit_ids_by_source.setdefault(key, []).append(u["unit_id"])

    selected_in_wave = [
        i for i in wave.selected if i.name in unit_ids_by_source
    ]
    payload = {
        "wave_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "status": "pending_apply",
        "policy": asdict(wave.policy),
        "docs": [
            {
                "name": i.name,
                "path": str(i.path),
                "genre": i.genre,
                "doc_type": i.doc_type,
                "unit_ids": unit_ids_by_source.get(i.name, []),
            }
            for i in selected_in_wave
        ],
        "batch_files": batch_files,
        "deferred": [i.name for i in wave.deferred],
        "remaining_inbox": wave.remaining_inbox,
    }
    path = tmp_dir / MANIFEST_NAME
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_wave_manifest(tmp_dir: Path) -> dict:
    path = tmp_dir / MANIFEST_NAME
    if not path.exists():
        raise FileNotFoundError(f"未找到 {path}，请先运行 compile 生成本波 prompt")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("wave-manifest.json 格式无效")
    return data


def mark_manifest_applied(tmp_dir: Path, manifest: dict) -> None:
    manifest = dict(manifest)
    manifest["status"] = "applied"
    (tmp_dir / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def format_plan_report(
    inventory: list[InventoryItem],
    policy: CompilePolicy,
    progress: dict,
) -> str:
    lines = [
        "=== /compile 分波计划 ===",
        (
            f"策略: max_chars={policy.max_chars}, wave_prompts={policy.wave_prompts}, "
            f"wave_docs={policy.wave_docs}, deep={policy.deep}, all={policy.process_all}"
        ),
        f"Inbox 文档数: {len(inventory)}",
        "",
        "库存：",
    ]
    for item in _sort_inventory(inventory):
        done = len(completed_unit_ids(progress, item.name))
        lines.append(
            f"  {item.name}  genre={item.genre}  chars≈{item.char_count}  done_units={done}"
        )

    wave = select_wave(inventory, policy, progress)
    lines.append("")
    lines.append(
        f"本波将处理 {len(wave.selected)} 篇 → {len(wave.batches)} 个 prompt；"
        f"约剩余 {wave.remaining_inbox} 篇/未完成源待后续波次"
    )
    for item in wave.selected:
        lines.append(f"  [本波] {item.name} ({item.genre})")
    for item in wave.deferred[:20]:
        lines.append(f"  [暂缓] {item.name} ({item.genre})")
    if len(wave.deferred) > 20:
        lines.append(f"  ... 另有 {len(wave.deferred) - 20} 篇暂缓")
    lines.append("=== 计划结束 ===")
    return "\n".join(lines)
