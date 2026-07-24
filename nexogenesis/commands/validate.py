from pathlib import Path

import click

from nexogenesis.schemas import validate_card_schema
from nexogenesis.store import Store
from nexogenesis.yaml_utils import split_frontmatter


def run_validate(root_path: Path) -> tuple[list[str], list[str]]:
    cards_dir = root_path / "01-Cards"
    store = Store(cards_dir).load()
    schema_errors: list[str] = []
    for card in store.cards.values():
        meta, _ = split_frontmatter(Path(card.path).read_text(encoding="utf-8"))
        errs = validate_card_schema(meta)
        for e in errs:
            schema_errors.append(f"{card.id}: {e}")
    semantic_errors, warnings = store.validate()
    return schema_errors + semantic_errors, warnings


@click.command()
@click.option("--root", default=".", help="项目根目录")
@click.option("--strict", is_flag=True, help="warning 也视为错误")
def validate_cmd(root: str, strict: bool):
    root_path = Path(root).resolve()
    all_errors, warnings = run_validate(root_path)

    for e in all_errors:
        click.echo(f"ERROR: {e}")
    for w in warnings:
        click.echo(f"WARNING: {w}")

    if all_errors or (strict and warnings):
        raise click.ClickException("Validation failed.")
    click.echo("Validation passed.")
