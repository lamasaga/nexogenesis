"""思维体能力评测题库：加载、schema 自检、任务×难度覆盖矩阵。

设计来源：04-OutBox/2026-08-04-思维体能力评测题库设计.md（P0 骨架）。
题库文件在 bank/*.yaml，每题一个 entry；由 test_bank.py 驱动执行。
"""
from __future__ import annotations

from pathlib import Path

import yaml

BANK_DIR = Path(__file__).resolve().parent / "bank"

TASK_TYPES = ("retrieve", "write_redteam", "dialogue_stm")
DIFFICULTIES = ("easy", "medium", "hard")

_TASK_REQUIRED = {
    "retrieve": ("query",),
    "write_redteam": ("batch",),
    "dialogue_stm": ("setup",),
}


def load_bank(bank_dir: Path | None = None) -> list[dict]:
    """加载全部题库条目（按文件名排序），每条附 _file 便于定位。"""
    bank_dir = Path(bank_dir) if bank_dir else BANK_DIR
    questions: list[dict] = []
    for f in sorted(bank_dir.glob("*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for q in data.get("questions") or []:
            q = dict(q)
            q["_file"] = f.name
            questions.append(q)
    return questions


def validate_bank(questions: list[dict]) -> list[str]:
    """schema 自检：id 唯一、task/difficulty 合法、必需字段在位、有 expect。"""
    errors: list[str] = []
    ids: set[str] = set()
    for q in questions:
        qid = q.get("id")
        if not qid:
            errors.append(f"{q.get('_file')}: 条目缺 id")
            continue
        if qid in ids:
            errors.append(f"{qid}: id 重复")
        ids.add(qid)
        task = q.get("task")
        if task not in TASK_TYPES:
            errors.append(f"{qid}: 未知 task={task!r}（合法值 {TASK_TYPES}）")
            continue
        if q.get("difficulty", "easy") not in DIFFICULTIES:
            errors.append(f"{qid}: 未知 difficulty={q.get('difficulty')!r}")
        for key in _TASK_REQUIRED[task]:
            if key not in q or q[key] in (None, ""):
                errors.append(f"{qid}: {task} 缺必需字段 {key}")
        if "expect" not in q:
            errors.append(f"{qid}: 缺 expect（无验收标准的题不入库）")
    return errors


def coverage_matrix(questions: list[dict]) -> dict[tuple[str, str], int]:
    """任务类型 × 难度 覆盖矩阵：哪格没题一目了然。"""
    cells: dict[tuple[str, str], int] = {}
    for q in questions:
        key = (str(q.get("task")), str(q.get("difficulty", "easy")))
        cells[key] = cells.get(key, 0) + 1
    return cells
