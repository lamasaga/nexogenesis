import click

from nexogenesis.commands.init import init_cmd
from nexogenesis.commands.validate import validate_cmd
from nexogenesis.commands.index import index_cmd
from nexogenesis.commands.write import write_cmd
from nexogenesis.commands.doctor import doctor_cmd
from nexogenesis.commands.migrate import migrate_cmd
from nexogenesis.commands.compile import compile_cmd
from nexogenesis.commands.digest import digest_cmd
from nexogenesis.commands.construct import construct_cmd


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Nexogenesis harness CLI."""
    pass


main.add_command(init_cmd, name="init")
main.add_command(validate_cmd, name="validate")
main.add_command(index_cmd, name="index")
main.add_command(write_cmd, name="write")
main.add_command(doctor_cmd, name="doctor")
main.add_command(migrate_cmd, name="migrate")
main.add_command(compile_cmd, name="compile")
main.add_command(digest_cmd, name="digest")
main.add_command(construct_cmd, name="construct")


if __name__ == "__main__":
    main()
