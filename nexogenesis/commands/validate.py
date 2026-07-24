import click


@click.command()
@click.option("--root", default=".", help="项目根目录")
@click.option("--strict", is_flag=True, help="warning 也视为错误")
def validate_cmd(root: str, strict: bool):
    click.echo("TODO: validate")
