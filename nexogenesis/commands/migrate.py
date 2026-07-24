import click


@click.command()
@click.option("--to", required=True, help="目标 scheme_id")
@click.option("--root", default=".", help="项目根目录")
@click.option("--dry-run", is_flag=True, default=True, help="只生成报告，不执行")
def migrate_cmd(to: str, root: str, dry_run: bool):
    click.echo("TODO: migrate")
