"""编译单元的批次组织、prompt 生成、LLM 返回解析与 Buffer 写入。"""

import logging
import re
from datetime import datetime
from pathlib import Path

import yaml

from nexogenesis.ingest import VALID_BUFFER_ROLES, count_chars
from nexogenesis.ingest.prompts import render_compile_prompt
from nexogenesis.schemas import CARD_TYPES


logger = logging.getLogger(__name__)

DEFAULT_ROLE = "meaning-unit"


def build_batches(units: list[dict], max_chars: int = 30000) -> list[list[dict]]:
    """将编译单元按 max_chars 上限分批。"""
    batches = []
    current = []
    current_chars = 0
    for unit in units:
        unit_chars = unit["char_count"]
        if unit_chars > max_chars:
            if current:
                batches.append(current)
                current = []
                current_chars = 0
            batches.append([unit])
            continue
        if current_chars + unit_chars > max_chars and current:
            batches.append(current)
            current = []
            current_chars = 0
        current.append(unit)
        current_chars += unit_chars
    if current:
        batches.append(current)
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


def parse_llm_buffers(raw_output: str, default_source: str) -> list[dict]:
    """解析 LLM 输出中的 Buffer 块。"""
    text = raw_output.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```\s*$", "", text)
        text = text.strip()

    if not text:
        raise ValueError("LLM 输出为空")

    buffers = []
    pos = 0
    while True:
        start = text.find("---", pos)
        if start == -1:
            break
        end = text.find("---", start + 3)
        if end == -1:
            break
        fm_text = text[start + 3:end].strip()

        try:
            fm = yaml.safe_load(fm_text)
            if not isinstance(fm, dict):
                raise ValueError("frontmatter 不是字典")
        except yaml.YAMLError as e:
            logger.warning("解析 frontmatter 失败：%s", e)
            pos = end + 3
            continue

        candidate = text.find("---", end + 3)
        next_start = -1
        while candidate != -1:
            fm_end_candidate = text.find("---", candidate + 3)
            if fm_end_candidate == -1:
                break
            candidate_fm_text = text[candidate + 3:fm_end_candidate].strip()
            try:
                candidate_fm = yaml.safe_load(candidate_fm_text)
                if isinstance(candidate_fm, dict) and "title" in candidate_fm:
                    next_start = candidate
                    break
            except yaml.YAMLError:
                pass
            candidate = text.find("---", candidate + 3)

        body = text[end + 3:next_start if next_start != -1 else len(text)].strip()

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

        pos = end + 3
        if next_start == -1:
            break

    if not buffers:
        raise ValueError("未从 LLM 输出中解析到任何 Buffer 块")

    return buffers


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
