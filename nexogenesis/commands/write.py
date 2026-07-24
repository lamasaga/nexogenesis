import click


@click.command()
@click.option("--batch", required=True, type=click.Path(exists=True), help="batch YAML 文件")
@click.option("--root", default=".", help="项目根目录")
def write_cmd(batch: str, root: str):
    click.echo("TODO: write")
