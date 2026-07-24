from pathlib import Path

import click

from nexogenesis.store import Store


@click.command()
@click.option("--root", default=".", help="项目根目录")
def doctor_cmd(root: str):
    root_path = Path(root).resolve()
    issues = []
    for d in ["01-Cards", "02-Profile", "06-Journal"]:
        if not (root_path / d).exists():
            issues.append(f"缺少目录: {d}")
    store = Store(root_path / "01-Cards").load()
    errors, warnings = store.validate()
    for e in errors:
        issues.append(e)
    for w in warnings:
        click.echo(f"WARNING: {w}")
    if issues:
        for i in issues:
            click.echo(f"ISSUE: {i}")
        raise click.ClickException("Doctor found issues.")
    click.echo("Doctor: OK")
