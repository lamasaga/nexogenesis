"""题库驱动评测：检索指标 / 写入红队 / STM 固定轮。

题库见 bank/*.yaml，加载与覆盖矩阵见 loader.py。
设计来源：04-OutBox/2026-08-04-思维体能力评测题库设计.md（P0 + STM 固定轮）。
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loader import coverage_matrix, load_bank, validate_bank  # noqa: E402

from nexogenesis.commands.init import init_cmd  # noqa: E402
from nexogenesis.commands.memory import memory_cmd  # noqa: E402
from nexogenesis.ingest.batch_auto import self_check_batch  # noqa: E402
from nexogenesis.retrieve.context_package import build_context_package  # noqa: E402

GOLD_DIR = Path(__file__).resolve().parent / "gold_cards"
QUESTIONS = load_bank()


def _build_gold_root(tmp_path: Path) -> Path:
    """init 项目骨架 + 拷入 gold_cards 迷你金库。"""
    runner = CliRunner()
    res = runner.invoke(init_cmd, ["--root", str(tmp_path)])
    assert res.exit_code == 0, res.output
    cards = tmp_path / "01-Cards"
    cards.mkdir(parents=True, exist_ok=True)
    for f in GOLD_DIR.glob("*.md"):
        shutil.copy(f, cards / f.name)
    return tmp_path


def _node_ids(pkg: dict) -> list[str]:
    return [n["id"] for n in (pkg.get("structure") or {}).get("nodes") or []]


def _seed_ids(pkg: dict) -> list[str]:
    return list((pkg.get("structure") or {}).get("seeds") or [])


# ---------- 题库自身健康 ----------

def test_bank_schema_and_coverage():
    errors = validate_bank(QUESTIONS)
    assert not errors, "\n".join(errors)
    cells = coverage_matrix(QUESTIONS)
    for task in ("retrieve", "write_redteam", "dialogue_stm"):
        assert any(k[0] == task for k in cells), f"任务类型无题：{task}"
    # 至少一档非 easy，防题库退化
    assert any(k[1] != "easy" for k in cells), "题库全 easy，覆盖矩阵失效"


# ---------- 检索题 ----------

@pytest.mark.parametrize(
    "q", [q for q in QUESTIONS if q["task"] == "retrieve"], ids=lambda q: q["id"]
)
def test_retrieve(q: dict, tmp_path: Path):
    root = _build_gold_root(tmp_path)
    pkg = build_context_package(
        root, query=q["query"], mode=q.get("mode", "talk"), use_rag=False
    )
    nodes = _node_ids(pkg)
    seeds = _seed_ids(pkg)
    hit_space = set(nodes) | set(seeds)
    exp = q["expect"]
    for cid in exp.get("nodes_contain") or []:
        assert cid in hit_space, (
            f"{q['id']}: 未命中 {cid}；nodes={nodes} seeds={seeds}"
        )
    if exp.get("nodes_empty"):
        assert not nodes, f"{q['id']}: 盲区题应零节点，实际 nodes={nodes}"
    relevant = set(exp.get("relevant") or [])
    max_noise = exp.get("seeds_max_noise")
    if max_noise is not None and relevant:
        noise = [s for s in seeds if s not in relevant]
        assert len(noise) <= max_noise, (
            f"{q['id']}: 种子噪声超标 {noise}（上限 {max_noise}）"
        )


# ---------- 写入红队 ----------

@pytest.mark.parametrize(
    "q", [q for q in QUESTIONS if q["task"] == "write_redteam"], ids=lambda q: q["id"]
)
def test_write_redteam(q: dict):
    errors = self_check_batch(
        q["batch"],
        mode=q.get("mode", "digest"),
        bootstrap=bool(q.get("bootstrap", False)),
        require_approved_by=False,
    )
    exp = q["expect"]
    if exp.get("expect_ok"):
        assert not errors, f"{q['id']}: 期望通过但被拦：{errors}"
    for frag in exp.get("errors_contain") or []:
        assert any(frag in e for e in errors), (
            f"{q['id']}: 缺少期望错误 {frag!r}；实际 {errors}"
        )


# ---------- 对话 / STM 固定轮 ----------

@pytest.mark.parametrize(
    "q", [q for q in QUESTIONS if q["task"] == "dialogue_stm"], ids=lambda q: q["id"]
)
def test_dialogue_stm(q: dict, tmp_path: Path):
    root = _build_gold_root(tmp_path)
    runner = CliRunner()
    setup = q["setup"]
    res = runner.invoke(
        memory_cmd, ["start", "--title", setup.get("title", "t"), "--root", str(root)]
    )
    assert res.exit_code == 0, res.output
    args = ["update", "--root", str(root)]
    if setup.get("focus"):
        args += ["--focus", setup["focus"]]
    for c in setup.get("cites") or []:
        args += ["--cite", c]
    res = runner.invoke(memory_cmd, args)
    assert res.exit_code == 0, res.output

    pkg = build_context_package(
        root, query=q.get("query", ""), mode="talk", use_rag=False, use_stm=True
    )
    hit_space = set(_node_ids(pkg)) | set(_seed_ids(pkg))
    for cid in q["expect"].get("nodes_contain") or []:
        assert cid in hit_space, (
            f"{q['id']}: STM 已引/焦点卡未进入视野；"
            f"nodes={_node_ids(pkg)} seeds={_seed_ids(pkg)}"
        )
