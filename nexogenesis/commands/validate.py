from pathlib import Path

import click

from nexogenesis.body_slots import validate_buffer_body, validate_card_body
from nexogenesis.schemas import validate_buffer_schema, validate_card_schema
from nexogenesis.store import Store
from nexogenesis.yaml_utils import split_frontmatter


def _validate_buffers(
    root_path: Path,
    *,
    body_slots_as_errors: bool = False,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    buffer_dir = root_path / "05-Buffer"
    if not buffer_dir.exists():
        return errors, warnings
    for path in sorted(buffer_dir.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta, body = split_frontmatter(text)
        if not meta:
            errors.append(f"{path}: 缺少 frontmatter")
            continue
        rel = path.relative_to(root_path).as_posix()
        for e in validate_buffer_schema(meta):
            errors.append(f"{rel}: {e}")
        if "[[" in (body or ""):
            errors.append(f"{rel}: Buffer 正文不得包含 [[ ]] 链接")
        role = meta.get("role")
        if isinstance(role, str):
            slot_errs = validate_buffer_body(role, body or "")
            target = errors if body_slots_as_errors else warnings
            for e in slot_errs:
                target.append(f"{rel}: {e}")
            parent = path.parent.name
            if parent not in ("05-Buffer",) and parent != role:
                warnings.append(f"{rel}: 目录名 {parent} 与 role {role} 不一致")
    return errors, warnings


def run_validate(
    root_path: Path,
    cards_dir_override: Path | None = None,
    *,
    buffer_body_as_errors: bool = False,
) -> tuple[list[str], list[str]]:
    cards_dir = cards_dir_override or (root_path / "01-Cards")
    store = Store(cards_dir).load()
    errors: list[str] = []
    warnings: list[str] = []

    for card in store.cards.values():
        meta, body = split_frontmatter(Path(card.path).read_text(encoding="utf-8"))
        for e in validate_card_schema(meta):
            errors.append(f"{card.id}: {e}")
        card_type = meta.get("type") if meta else None
        if isinstance(card_type, str):
            slot_errs = validate_card_body(card_type, body or "")
            if body and len(body.strip()) > 20:
                for e in slot_errs:
                    errors.append(f"{card.id}: {e}")
            else:
                for e in slot_errs:
                    warnings.append(f"{card.id}: {e}")
        if meta:
            theory = meta.get("theory_status")
            if theory and card_type in ("claim", "model"):
                if "失效边界" not in (body or "") and "原文未提及" not in (body or ""):
                    errors.append(f"{card.id}: theory_status 要求正文含「失效边界」或「原文未提及」")

    semantic_errors, store_warnings = store.validate()
    buf_errors, buf_warnings = _validate_buffers(
        root_path, body_slots_as_errors=buffer_body_as_errors
    )
    return errors + semantic_errors + buf_errors, warnings + store_warnings + buf_warnings


@click.command()
@click.option("--root", default=".", help="项目根目录")
@click.option("--strict", is_flag=True, help="warning 也视为错误")
@click.option(
    "--strict-buffer-body",
    is_flag=True,
    help="Buffer 语义槽缺失视为错误（默认仅 warning）",
)
def validate_cmd(root: str, strict: bool, strict_buffer_body: bool):
    root_path = Path(root).resolve()
    all_errors, warnings = run_validate(
        root_path, buffer_body_as_errors=strict_buffer_body
    )

    for e in all_errors:
        click.echo(f"ERROR: {e}")
    for w in warnings:
        click.echo(f"WARNING: {w}")

    if all_errors or (strict and warnings):
        raise click.ClickException("Validation failed.")
    click.echo("Validation passed.")
