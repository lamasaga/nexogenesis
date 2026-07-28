"""统一原子写入入口：先 staging 校验，再提交。"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import click

from nexogenesis import journal
from nexogenesis.commands.index import generate_indexes
from nexogenesis.commands.validate import run_validate
from nexogenesis.operations import BatchOperation, card_meta_from_write
from nexogenesis.yaml_utils import atomic_write_file, merge_frontmatter, split_frontmatter

WIKILINK_RE = re.compile(r"\[\[([^\]|#/]+)")


def _append_profile_question_content(existing: str | None, item: dict) -> str:
    if existing:
        lines = existing.splitlines()
    else:
        lines = ["# 问题清单", "", "| 问题 | 提出时间 | 状态 |", "|---|---|---|"]
    lines.append(f"| {item['question']} | {item.get('added_at', '')} | active |")
    return "\n".join(lines) + "\n"


def _preserve_created(cards_dir: Path, item: dict, meta: dict) -> None:
    final_path = cards_dir / f"{item['id']}.md"
    if not final_path.exists():
        return
    old_meta, _ = split_frontmatter(final_path.read_text(encoding="utf-8"))
    if old_meta.get("created"):
        meta["created"] = old_meta["created"]


def _check_write_permissions(batch_op: BatchOperation) -> list[str]:
    errors: list[str] = []
    allow_promo = bool(getattr(batch_op, "allow_system_promotion", False))
    for item in batch_op.writes:
        if item.get("target", "card") != "card":
            continue
        origin = item.get("origin")
        maturity = item.get("maturity")
        theory = item.get("theory_status")
        if origin == "system" and (maturity == "mature" or theory == "active"):
            if not allow_promo or batch_op.approved_by != "user":
                errors.append(
                    f"{item.get('id')}: origin=system 进入 mature/theory_status=active "
                    "需要 approved_by=user 且 operation.allow_system_promotion: true"
                )
        body = item.get("body") or ""
        if theory and "失效边界" not in body and "原文未提及" not in body:
            errors.append(f"{item.get('id')}: 设置 theory_status 时正文须含「失效边界」或「原文未提及」")
    return errors


def _check_wikilinks_in_writes(batch_op: BatchOperation, known_ids: set[str]) -> list[str]:
    errors: list[str] = []
    staged_ids = {
        w["id"] for w in batch_op.writes if w.get("target", "card") == "card" and "id" in w
    }
    all_ids = known_ids | staged_ids
    for item in batch_op.writes:
        if item.get("target", "card") != "card":
            continue
        body = item.get("body") or ""
        for m in WIKILINK_RE.finditer(body):
            target = m.group(1).strip()
            if target and target not in all_ids:
                errors.append(f"{item.get('id')}: 正文幽灵链接 [[{target}]]")
    return errors


@click.command()
@click.option("--batch", required=True, type=click.Path(exists=True), help="batch YAML 文件")
@click.option("--root", default=".", help="项目根目录")
def write_cmd(batch: str, root: str):
    root_path = Path(root).resolve()
    cards_dir = root_path / "01-Cards"
    cards_dir.mkdir(parents=True, exist_ok=True)
    profile_path = root_path / "02-Profile" / "问题清单.md"
    batch_op = BatchOperation.from_file(Path(batch))

    card_writes = [w for w in batch_op.writes if w.get("target", "card") == "card"]
    profile_writes = [w for w in batch_op.writes if w.get("target") == "profile_question"]

    pre_errors = _check_write_permissions(batch_op)
    if pre_errors:
        raise click.ClickException("Write rejected:\n" + "\n".join(pre_errors))

    # 已有卡片 id（用于幽灵链接检查）
    known_ids = {p.stem for p in cards_dir.glob("*.md") if not p.name.startswith("_")}
    link_errors = _check_wikilinks_in_writes(batch_op, known_ids)
    if link_errors:
        raise click.ClickException("Write rejected:\n" + "\n".join(link_errors))

    staging = root_path / ".nexogenesis" / "tmp" / f"write-{batch_op.operation_id}"
    if staging.exists():
        shutil.rmtree(staging)
    staging_cards = staging / "01-Cards"
    staging_cards.mkdir(parents=True)
    staging_meta = staging_cards / "_meta"
    staging_meta.mkdir(parents=True, exist_ok=True)

    # 复制现有卡片到 staging（仅 md，不含深层无关）
    for path in cards_dir.glob("*.md"):
        if path.name.startswith("_"):
            continue
        shutil.copy2(path, staging_cards / path.name)
    src_meta = cards_dir / "_meta"
    if src_meta.exists():
        for path in src_meta.glob("*.md"):
            shutil.copy2(path, staging_meta / path.name)

    # 写入本批卡片到 staging（保留已有 created）
    for item in card_writes:
        meta = card_meta_from_write(item)
        _preserve_created(cards_dir, item, meta)
        content = merge_frontmatter(meta, item.get("body", ""))
        atomic_write_file(staging_cards / f"{item['id']}.md", content)

    # 准备 profile 新内容（仅内存/staging，成功后再落盘）
    staged_profile: str | None = None
    if profile_writes:
        existing = profile_path.read_text(encoding="utf-8") if profile_path.exists() else None
        staged_profile = existing
        for pw in profile_writes:
            staged_profile = _append_profile_question_content(staged_profile, pw)
        staging_profile = staging / "02-Profile"
        staging_profile.mkdir(parents=True, exist_ok=True)
        atomic_write_file(staging_profile / "问题清单.md", staged_profile)

    # 用 staging 作为卡片目录做校验；Buffer 仍读真实 root
    try:
        errors, warnings = run_validate(root_path, cards_dir_override=staging_cards)
        if errors:
            raise RuntimeError("; ".join(errors))

        # 提交：卡片
        for item in card_writes:
            src = staging_cards / f"{item['id']}.md"
            atomic_write_file(cards_dir / f"{item['id']}.md", src.read_text(encoding="utf-8"))

        # 提交：问题清单
        if staged_profile is not None:
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_file(profile_path, staged_profile)

        journal.append(
            root_path,
            batch_op.operation_id,
            "write",
            [w["id"] for w in card_writes],
            batch_op.source,
            batch_op.approved_by,
        )
        generate_indexes(root_path)
        from nexogenesis.indexing import refresh_derived_indexes

        refresh_derived_indexes(
            root_path,
            graph=True,
            rag=True,
            rag_kinds=["card_excerpt", "buffer", "archive", "discussion", "outbox"],
            quiet=True,
        )
    except Exception as exc:
        raise click.ClickException(f"Write failed (no commit): {exc}") from exc
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)

    for w in warnings:
        click.echo(f"WARNING: {w}")
    click.echo(f"Wrote {len(card_writes)} card(s), {len(profile_writes)} question(s).")
