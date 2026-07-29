"""digest/construct --auto：batch 自检、授权戳记、规程文件。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from nexogenesis.ingest.structure_signals import LENSES
from nexogenesis.yaml_utils import atomic_write_file

CARD_REQUIRED = (
    "id",
    "title",
    "type",
    "maturity",
    "lifecycle",
    "domains",
    "origin",
    "body",
    "created",
    "updated",
)


def load_batch_data(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("batch 根节点必须是 mapping")
    return data


def stamp_approved_by(path: Path, approved_by: str = "agent") -> str:
    """写入/覆盖 operation.approved_by；若已是 user 则保留。返回最终值。"""
    data = load_batch_data(path)
    op = data.setdefault("operation", {})
    if not isinstance(op, dict):
        raise ValueError("operation 必须是 mapping")
    current = str(op.get("approved_by") or "").strip()
    if current == "user":
        final = "user"
    else:
        final = approved_by
        op["approved_by"] = final
    text = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    atomic_write_file(path, text)
    return final


def self_check_batch(
    data: dict[str, Any],
    *,
    mode: str,
    bootstrap: bool = False,
    require_approved_by: bool = True,
) -> list[str]:
    """返回错误列表；空列表表示可通过 --auto 落盘。"""
    errors: list[str] = []
    op = data.get("operation")
    if not isinstance(op, dict):
        return ["缺少 operation mapping"]
    for key in ("id", "source"):
        if not str(op.get(key) or "").strip():
            errors.append(f"operation.{key} 缺失或为空")
    if require_approved_by and not str(op.get("approved_by") or "").strip():
        errors.append("operation.approved_by 缺失或为空")

    writes = data.get("writes")
    if writes is None:
        errors.append("缺少 writes")
        return errors
    if not isinstance(writes, list):
        errors.append("writes 必须是列表")
        return errors
    if not writes:
        errors.append("writes 为空：--auto 拒绝空 batch（无实质写入）")

    consumed = op.get("consumed_buffers")
    if mode == "digest":
        if not isinstance(consumed, list) or not consumed:
            errors.append("digest 须在 operation.consumed_buffers 声明实际消费的 Buffer 路径")

    seen_domain_write = False
    for i, item in enumerate(writes):
        if not isinstance(item, dict):
            errors.append(f"writes[{i}] 不是 mapping")
            continue
        target = item.get("target")
        if target == "profile_question":
            if not str(item.get("question") or "").strip():
                errors.append(f"writes[{i}] profile_question 缺少 question")
            continue
        if target != "card":
            errors.append(f"writes[{i}] 未知 target={target!r}")
            continue
        for key in CARD_REQUIRED:
            if key not in item or item[key] is None or item[key] == "":
                errors.append(f"writes[{i}] card 缺少 {key}")
        domains = item.get("domains")
        if domains is not None and (not isinstance(domains, list) or not domains):
            errors.append(f"writes[{i}] domains 须为非空列表")

        ctype = str(item.get("type") or "")
        if ctype == "domain":
            seen_domain_write = True

        origin = str(item.get("origin") or "")
        maturity = str(item.get("maturity") or "")
        theory = str(item.get("theory_status") or "")
        if origin == "system" and (
            maturity == "mature" or theory == "active"
        ):
            allow = bool(op.get("allow_system_promotion"))
            if allow and str(op.get("approved_by")) != "user":
                errors.append(
                    f"writes[{i}] system 升格须 approved_by=user 且 allow_system_promotion"
                )
            elif not allow:
                errors.append(
                    f"writes[{i}] --auto 拒绝 origin=system 进入 mature/theory active"
                )

    if mode == "digest" and bootstrap and writes:
        card_writes = [
            w for w in writes if isinstance(w, dict) and w.get("target") == "card"
        ]
        types = [str(w.get("type") or "") for w in card_writes]
        if types:
            if "domain" not in types and not seen_domain_write:
                errors.append("空库/无 domain：batch 须包含至少一张 domain 卡")
            elif types[0] != "domain":
                errors.append("空库 bootstrap：第一个 card write 必须是 domain")

    return errors


def suggest_lenses(signals: dict[str, list[str]], *, max_lenses: int = 3) -> list[str]:
    """按信号强度选出本轮建议执行的镜头（不含 all）。优先补边/involves/枢纽。"""
    scored: list[tuple[int, str]] = []
    for lens in LENSES:
        items = list(signals.get(lens) or [])
        if not items:
            continue
        if lens == "cross_source" and all("可暂缓" in s or "来源较单一" in s for s in items):
            continue
        weight = len(items)
        blob = "\n".join(items)
        if lens == "distinguish" and any(
            k in blob
            for k in ("require_involves", "involves", "tension", "conflict", "conflicts-with")
        ):
            weight += 3
        if lens == "articulate" and any(
            k in blob for k in ("suggest_entity_hub", "枢纽", "链接空洞", "bridge")
        ):
            weight += 2
        if lens == "cluster" and any(
            k in blob for k in ("空壳", "无成员", "suggest_link_or_enrich", "orphan")
        ):
            weight += 1
        scored.append((weight, lens))
    scored.sort(key=lambda x: (-x[0], LENSES.index(x[1])))
    return [lens for _, lens in scored[:max_lenses]]


def write_digest_runbook(tmp_dir: Path, *, batch_path: Path, prompt_path: Path) -> Path:
    text = (
        "# digest --auto 规程\n\n"
        "用户「开始消化」或 `digest --auto` 视为本轮写入授权。"
        "中间产物保留供事后分析；无需逐步人工确认。\n\n"
        "## Agent 步骤\n\n"
        f"1. 阅读 `{prompt_path.as_posix()}`\n"
        "2. 调用 LLM，产出标准 `write --batch` YAML\n"
        f"3. 保存到 `{batch_path.as_posix()}`\n"
        "4. 自检：YAML 可解析、`consumed_buffers` 已声明、空库先写 domain\n"
        "5. 不合格则改 batch / 重跑 LLM，不要停下来等人\n"
        "6. 再执行：`python -m nexogenesis digest --auto --root .`\n"
        "   （有 batch 时 Harness 自检通过后自动 `--apply`，`approved_by` 记 `agent`；"
        "若 batch 已写 `user` 则保留）\n\n"
        "## 事后分析\n\n"
        "- `prompt.md` / `batch.yaml` / 本文件均保留在本目录\n"
    )
    path = tmp_dir / "auto-runbook.md"
    atomic_write_file(path, text)
    return path


def write_construct_runbook(
    tmp_dir: Path,
    *,
    suggested: list[str],
    batch_path: Path,
) -> Path:
    lenses = ", ".join(suggested) if suggested else "（诊断无强信号，可人工选 lens）"
    lines = [
        "# construct --auto 规程\n",
        "用户「开始建构」或 `construct --auto` 视为本轮写入授权。"
        "中间产物保留供事后分析。\n",
        "## Agent 步骤（行动优先，勿空谈）\n",
        "0. 阅读 `structure-ops-draft.md`：若 seed-links 非空，先执行 "
        "`python -m nexogenesis construct --apply-seed-links --root .`\n"
        "   （确定性挂 domain；也可直接 write `structure-seed-links.yaml`）\n",
        "1. 阅读 `lenses-report.md`、`structure-ops-llm.yaml`、`suggested-lenses.txt`\n",
        "2. distinguish：把 `require_involves` 写成完整 enrich（involves 落到 claim/model）\n",
        "3. articulate：处理 `suggest_entity_hub`（升格 entity/补强 model + based-on，"
        "不是新类型「概念」）与链接空洞\n",
        f"4. 建议镜头（按序，一次一个）：{lenses}\n",
        "5. 对每个镜头：`construct --lens <name>` → LLM → 写 `batch.yaml` → "
        "`construct --auto --lens <name>`（有 batch 则自检并 apply）\n",
        "6. 自检不合格则改写/重跑，不要逐步等人确认\n",
        f"7. batch 路径：`{batch_path.as_posix()}`\n",
        "\n## 事后分析\n\n"
        "- `structure-ops-draft.md` / `structure-seed-links.yaml` / "
        "`structure-ops-llm.yaml` / `lenses-report.md` / 各次 `prompt.md` / `batch.yaml` 均保留\n",
    ]
    path = tmp_dir / "auto-runbook.md"
    atomic_write_file(path, "".join(lines))
    return path
