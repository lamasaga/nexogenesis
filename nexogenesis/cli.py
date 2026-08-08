import sys

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
from nexogenesis.commands.serve import serve_cmd


def ensure_utf8_stdio() -> None:
    """
    Windows 控制台常为 gbk：click.echo 输出中文路径/扩展字符会 UnicodeEncodeError。
    在 CLI 入口统一把 stdout/stderr 切到 utf-8（失败字符替换，不中断命令）。
    """
    for stream in (sys.stdout, sys.stderr):
        if stream is None:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        encoding = (getattr(stream, "encoding", None) or "").lower()
        if encoding in ("utf-8", "utf8"):
            try:
                reconfigure(errors="replace")
            except (OSError, ValueError, AttributeError):
                pass
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError, AttributeError):
            pass


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Nexogenesis harness CLI."""
    ensure_utf8_stdio()


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
main.add_command(serve_cmd, name="serve")


if __name__ == "__main__":
    main()
