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
from nexogenesis.commands.graph import graph_cmd
from nexogenesis.commands.rag import rag_cmd
from nexogenesis.commands.retrieve import retrieve_cmd
from nexogenesis.commands.memory import attention_cmd, memory_cmd, signal_cmd


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
main.add_command(graph_cmd, name="graph")
main.add_command(rag_cmd, name="rag")
main.add_command(retrieve_cmd, name="retrieve")
main.add_command(memory_cmd, name="memory")
main.add_command(attention_cmd, name="attention")
main.add_command(signal_cmd, name="signal")


if __name__ == "__main__":
    main()
