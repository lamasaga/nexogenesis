"""编译单元的批次组织、prompt 生成、LLM 返回解析与 Buffer 写入。"""

import logging
import re
from datetime import datetime
from pathlib import Path

import yaml

from nexogenesis.ingest import VALID_BUFFER_TYPES, count_chars
from nexogenesis.ingest.prompts import render_compile_prompt


logger = logging.getLogger(__name__)


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

        btype = fm.get("type", "claim")
        if btype not in VALID_BUFFER_TYPES:
            logger.warning("非法 Buffer type '%s'，回退到 claim", btype)
            btype = "claim"

        buffers.append({
            "title": str(fm.get("title", "未命名碎片")),
            "type": btype,
            "source": str(fm.get("source", default_source)),
            "genre": str(fm["genre"]) if fm.get("genre") else None,
            "perspective": str(fm["perspective"]) if fm.get("perspective") else None,
            "proposed_domains": list(fm["proposed_domains"]) if isinstance(fm.get("proposed_domains"), list) else [],
            "proposed_maturity": str(fm["proposed_maturity"]) if fm.get("proposed_maturity") else None,
            "body": body,
        })

        pos = end + 3
        if next_start == -1:
            break

    if not buffers:
        raise ValueError("未从 LLM 输出中解析到任何 Buffer 块")

    return buffers


def _sanitize_filename(title: str) -> str:
    s = re.sub(r"[<>:/\\|?*\"'\n]", "", title)
    s = s.strip().replace(" ", "-")
    return s[:50] or "untitled"


def write_buffer(buffer: dict, subtype: str, buffer_dir: Path, now: datetime | None = None) -> Path:
    """写入单个 Buffer 文件。"""
    if now is None:
        now = datetime.now()

    btype = buffer.get("type", "claim")
    if btype not in VALID_BUFFER_TYPES:
        logging.warning("非法 Buffer type '%s'，回退到 claim", btype)
        btype = "claim"
    if subtype not in VALID_BUFFER_TYPES:
        subtype = btype

    safe_title = _sanitize_filename(buffer["title"])
    filename = now.strftime(f"%Y-%m-%d-%H%M%S-%f-{safe_title}.md")
    target_dir = buffer_dir / subtype
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / filename

    frontmatter = {
        "title": buffer["title"],
        "type": btype,
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
    if buffer.get("proposed_maturity"):
        frontmatter["proposed_maturity"] = buffer["proposed_maturity"]

    content = "---\n" + yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False) + "---\n\n" + buffer["body"]
    target.write_text(content, encoding="utf-8")
    return target
