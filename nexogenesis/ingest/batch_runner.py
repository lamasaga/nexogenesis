"""编译单元的批次组织、prompt 生成、LLM 返回解析与 Buffer 写入。"""

import logging
import re
from datetime import datetime
from pathlib import Path

import yaml

from nexogenesis.body_slots import buffer_substance_warnings, validate_buffer_body
from nexogenesis.ingest import VALID_BUFFER_ROLES, count_chars
from nexogenesis.ingest.prompts import render_compile_prompt
from nexogenesis.schemas import CARD_TYPES, validate_buffer_schema


logger = logging.getLogger(__name__)

DEFAULT_ROLE = "meaning-unit"

# 同批最多混装的源文件数（按体裁）
MAX_DOCS_PER_BATCH = {
    "scrap": 3,
    "generic": 3,
    "dialogue": 1,
    "essay": 1,
    "paper": 1,
    "book": 1,
}


def max_docs_for_genre(genre: str | None) -> int:
    if not genre:
        return 1
    return MAX_DOCS_PER_BATCH.get(genre, 1)


def _unit_source_key(unit: dict) -> str:
    path = unit.get("source_path")
    if path is None:
        return ""
    return str(path)


def _flush_batch(batches: list, current: list) -> list:
    if current:
        batches.append(current)
    return []


def build_batches(
    units: list[dict],
    max_chars: int = 10000,
    *,
    group_by_genre: bool = True,
    max_docs_per_batch: int | None = None,
    max_docs_per_batch_fn=None,
) -> list[list[dict]]:
    """将编译单元装箱。

    - 默认按 genre 分组，且限制同批源文件数（避免 scrap+paper 混装、跨书混装）。
    - max_docs_per_batch 为全局上限；max_docs_per_batch_fn(genre) 可按体裁覆盖。
    """
    if max_chars <= 0:
        raise ValueError("max_chars 必须为正数")

    if group_by_genre:
        groups: dict[str, list[dict]] = {}
        order: list[str] = []
        for unit in units:
            genre = unit.get("genre") or "generic"
            if genre not in groups:
                groups[genre] = []
                order.append(genre)
            groups[genre].append(unit)
        batches: list[list[dict]] = []
        for genre in order:
            cap = max_docs_per_batch
            if cap is None and max_docs_per_batch_fn is not None:
                cap = max_docs_per_batch_fn(genre)
            if cap is None:
                cap = max_docs_for_genre(genre)
            batches.extend(
                _pack_group(groups[genre], max_chars=max_chars, max_docs=cap)
            )
        return batches

    cap = max_docs_per_batch if max_docs_per_batch is not None else 0
    return _pack_group(units, max_chars=max_chars, max_docs=cap or 10**9)


def _pack_group(units: list[dict], *, max_chars: int, max_docs: int) -> list[list[dict]]:
    batches: list[list[dict]] = []
    current: list[dict] = []
    current_chars = 0
    current_sources: set[str] = set()

    for unit in units:
        unit_chars = unit["char_count"]
        source = _unit_source_key(unit)
        # book：不同源文件永不混装
        genre = unit.get("genre")
        if genre == "book" and current_sources and source not in current_sources:
            current = _flush_batch(batches, current)
            current_chars = 0
            current_sources = set()

        would_new_source = source and source not in current_sources
        if would_new_source and current_sources and len(current_sources) >= max_docs:
            current = _flush_batch(batches, current)
            current_chars = 0
            current_sources = set()

        if unit_chars > max_chars:
            current = _flush_batch(batches, current)
            current_chars = 0
            current_sources = set()
            batches.append([unit])
            continue

        if current_chars + unit_chars > max_chars and current:
            current = _flush_batch(batches, current)
            current_chars = 0
            current_sources = set()
            # 换批后重新检查混装上限
            would_new_source = bool(source)

        current.append(unit)
        current_chars += unit_chars
        if source:
            current_sources.add(source)

    _flush_batch(batches, current)
    return batches


def format_batch_prompt(units: list[dict], genre: str | None = None, deep: bool = False) -> str:
    """将一批编译单元格式化为给 LLM 的提示词。"""
    return render_compile_prompt(units, genre=genre, deep=deep)


def _normalize_role(fm: dict) -> str:
    """从 frontmatter 解析 role；兼容旧 type=七型 写法。"""
    role = fm.get("role")
    if isinstance(role, str) and role in VALID_BUFFER_ROLES:
        return role
    legacy = fm.get("type")
    if isinstance(legacy, str) and legacy in VALID_BUFFER_ROLES:
        return legacy
    if isinstance(legacy, str) and legacy in CARD_TYPES:
        # 旧输出：type 为 Card 七型 → 降为意义单元，并把原 type 记为建议
        return DEFAULT_ROLE
    if isinstance(legacy, str):
        logger.warning("非法 Buffer role/type '%s'，回退到 %s", legacy, DEFAULT_ROLE)
    return DEFAULT_ROLE


def _line_number_at(text: str, offset: int) -> int:
    return text.count("\n", 0, max(0, offset)) + 1


def parse_llm_buffers(raw_output: str, default_source: str) -> list[dict]:
    """解析 LLM 输出中的 Buffer 块。

    使用单独成行的 ``---`` 作为 frontmatter 边界，避免把正文中的
    水平线或表格分隔线 ``|---|`` 误认为新块开始；统一 CRLF。
    """
    text = raw_output.strip().replace("\r\n", "\n").replace("\r", "\n")
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```\s*$", "", text)
        text = text.strip()

    if not text:
        raise ValueError("LLM 输出为空")

    dividers = [m.start() for m in re.finditer(r"^---\s*$", text, re.MULTILINE)]
    buffers = []
    parse_notes: list[str] = []
    idx = 0
    while idx < len(dividers) - 1:
        start = dividers[idx]
        fm = None
        end = None
        last_yaml_err = None
        for j in range(idx + 1, len(dividers)):
            candidate_end = dividers[j]
            fm_text = text[start + 3 : candidate_end].strip()
            try:
                candidate_fm = yaml.safe_load(fm_text)
                if isinstance(candidate_fm, dict):
                    fm = candidate_fm
                    end = candidate_end
                    break
            except yaml.YAMLError as e:
                last_yaml_err = e
                continue

        if fm is None or end is None:
            line = _line_number_at(text, start)
            if last_yaml_err:
                parse_notes.append(f"约第 {line} 行：frontmatter YAML 无效（{last_yaml_err}）")
            idx += 1
            continue

        next_start = None
        end_idx = dividers.index(end)
        for k in range(end_idx + 1, len(dividers)):
            candidate_next = dividers[k]
            fm_end_candidate = None
            for m in range(k + 1, len(dividers)):
                if dividers[m] > candidate_next:
                    fm_end_candidate = dividers[m]
                    break
            if fm_end_candidate is None:
                break
            candidate_fm_text = text[candidate_next + 3 : fm_end_candidate].strip()
            try:
                candidate_fm = yaml.safe_load(candidate_fm_text)
                if isinstance(candidate_fm, dict) and "title" in candidate_fm:
                    next_start = candidate_next
                    break
            except yaml.YAMLError:
                continue

        body = text[end + 3 : next_start if next_start is not None else len(text)].strip()

        role = _normalize_role(fm)
        proposed_card_type = fm.get("proposed_card_type")
        legacy_type = fm.get("type")
        if not proposed_card_type and isinstance(legacy_type, str) and legacy_type in CARD_TYPES:
            proposed_card_type = legacy_type
        if isinstance(proposed_card_type, str) and proposed_card_type not in CARD_TYPES:
            proposed_card_type = None

        buffers.append({
            "title": str(fm.get("title", "未命名质料")),
            "role": role,
            "source": str(fm.get("source", default_source)),
            "genre": str(fm["genre"]) if fm.get("genre") else None,
            "perspective": str(fm["perspective"]) if fm.get("perspective") else None,
            "proposed_domains": list(fm["proposed_domains"]) if isinstance(fm.get("proposed_domains"), list) else [],
            "proposed_card_type": proposed_card_type,
            "related_within_batch": list(fm["related_within_batch"]) if isinstance(fm.get("related_within_batch"), list) else [],
            "body": body,
        })

        idx = end_idx + 1
        if next_start is not None:
            idx = dividers.index(next_start)

    if not buffers:
        hint = ("；".join(parse_notes[:3]) + ("…" if len(parse_notes) > 3 else "")) if parse_notes else ""
        raise ValueError("未从 LLM 输出中解析到任何 Buffer 块" + (f"。{hint}" if hint else ""))

    for note in parse_notes:
        logger.warning("%s", note)

    return buffers


def load_response_raw(path: Path) -> str:
    """读取 response 文件；支持纯 markdown 或 YAML {\"output\": \"...\"}。"""
    raw = path.read_bytes()
    if b"\x00" in raw:
        raw = raw.replace(b"\x00", b"")
    text = raw.decode("utf-8", errors="replace")
    try:
        data = yaml.safe_load(text)
        if isinstance(data, dict) and "output" in data:
            return str(data["output"])
    except yaml.YAMLError:
        pass
    return text


def inspect_response_buffers(
    buffers: list[dict],
    *,
    strict_body: bool = False,
) -> tuple[list[str], list[str]]:
    """对已解析 Buffer 做结构/槽检查。返回 (hard_errors, warnings)。"""
    hard: list[str] = []
    soft: list[str] = []
    for i, buf in enumerate(buffers, 1):
        prefix = f"块{i}({buf.get('title', '?')})"
        meta = {
            "title": buf["title"],
            "role": buf["role"],
            "source": buf["source"],
            "created": "1970-01-01",
            "updated": "1970-01-01",
            "status": "scratch",
        }
        if buf.get("genre"):
            meta["genre"] = buf["genre"]
        if buf.get("perspective"):
            meta["perspective"] = buf["perspective"]
        if buf.get("proposed_domains"):
            meta["proposed_domains"] = buf["proposed_domains"]
        if buf.get("proposed_card_type"):
            meta["proposed_card_type"] = buf["proposed_card_type"]
        for e in validate_buffer_schema(meta):
            hard.append(f"{prefix}: {e}")
        body = buf.get("body") or ""
        if "[[" in body:
            hard.append(f"{prefix}: Buffer 正文不得包含 [[ ]] 链接")
        slot_errs = validate_buffer_body(buf["role"], body)
        if strict_body:
            hard.extend(f"{prefix}: {e}" for e in slot_errs)
        else:
            soft.extend(f"{prefix}: {e}" for e in slot_errs)
        for w in buffer_substance_warnings(
            role=str(buf.get("role") or ""),
            title=str(buf.get("title") or ""),
            body=body,
        ):
            soft.append(f"{prefix}: {w}")
    return hard, soft


def check_response_file(
    path: Path,
    *,
    default_source: str = "00-Inbox compile",
    strict_body: bool = False,
) -> tuple[list[dict], list[str], list[str]]:
    """解析并检查单个 response。返回 (buffers, hard_errors, warnings)。"""
    try:
        raw = load_response_raw(path)
        buffers = parse_llm_buffers(raw, default_source=default_source)
    except Exception as e:
        return [], [f"{path.name}: 解析失败 — {e}"], []
    hard, soft = inspect_response_buffers(buffers, strict_body=strict_body)
    hard = [f"{path.name}: {e}" for e in hard]
    soft = [f"{path.name}: {e}" for e in soft]
    return buffers, hard, soft


def _sanitize_filename(title: str) -> str:
    s = re.sub(r'[<>:/\\|?*"\'\n\r\t]', "", title)
    s = s.strip().replace(" ", "-")
    return s[:50] or "untitled"


def write_buffer(buffer: dict, subtype: str | None = None, buffer_dir: Path | None = None, now: datetime | None = None) -> Path:
    """写入单个 Buffer 文件。subtype 为 role 子目录名。"""
    if now is None:
        now = datetime.now()
    if buffer_dir is None:
        raise ValueError("buffer_dir is required")

    role = buffer.get("role") or subtype or DEFAULT_ROLE
    if role not in VALID_BUFFER_ROLES:
        logging.warning("非法 Buffer role '%s'，回退到 %s", role, DEFAULT_ROLE)
        role = DEFAULT_ROLE
    if subtype and subtype in VALID_BUFFER_ROLES:
        role = subtype
    elif subtype and subtype not in VALID_BUFFER_ROLES:
        role = role if role in VALID_BUFFER_ROLES else DEFAULT_ROLE

    safe_title = _sanitize_filename(buffer["title"])
    target_dir = buffer_dir / role
    target_dir.mkdir(parents=True, exist_ok=True)
    seq = 0
    while True:
        seq += 1
        filename = now.strftime(f"%Y-%m-%d-%H%M%S-{seq:02d}-{safe_title}.md")
        target = target_dir / filename
        if not target.exists():
            break

    frontmatter = {
        "title": buffer["title"],
        "role": role,
        "created": now.strftime("%Y-%m-%d"),
        "updated": now.strftime("%Y-%m-%d"),
        "source": buffer["source"],
        "status": "scratch",
    }
    if buffer.get("genre"):
        frontmatter["genre"] = buffer["genre"]
    if buffer.get("perspective"):
        frontmatter["perspective"] = buffer["perspective"]
    if buffer.get("proposed_domains"):
        frontmatter["proposed_domains"] = buffer["proposed_domains"]
    if buffer.get("proposed_card_type"):
        frontmatter["proposed_card_type"] = buffer["proposed_card_type"]
    if buffer.get("related_within_batch"):
        frontmatter["related_within_batch"] = buffer["related_within_batch"]

    content = "---\n" + yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False) + "---\n\n" + buffer["body"]
    target.write_text(content, encoding="utf-8")
    return target
