import click


@click.command()
@click.option("--root", default=".", help="项目根目录")
def init_cmd(root: str):
    click.echo("TODO: init")
