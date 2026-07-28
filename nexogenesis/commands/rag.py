from pathlib import Path

import click

from nexogenesis.rag.index import index_rag, rag_stats
from nexogenesis.rag.search import rag_search


@click.group()
def rag_cmd():
    """质料 RAG（FTS）索引与检索。"""
    pass


@rag_cmd.command("index")
@click.option("--root", default=".", help="项目根目录")
@click.option("--full", is_flag=True, help="全量重建索引（默认增量）")
@click.option(
    "--kinds",
    default="archive,buffer,discussion,outbox,card_excerpt",
    show_default=True,
    help="逗号分隔语料类型",
)
def rag_index(root: str, full: bool, kinds: str):
    kind_list = [k.strip() for k in kinds.split(",") if k.strip()]
    stats = index_rag(
        Path(root).resolve(),
        kinds=kind_list,
        full=full,
        incremental=not full,
    )
    click.echo(
        f"RAG indexed: chunks={stats.get('chunk_count')} "
        f"updated_paths={stats.get('updated_paths')} "
        f"incremental={stats.get('incremental')}"
    )


@rag_cmd.command("stats")
@click.option("--root", default=".", help="项目根目录")
def rag_stats_cmd(root: str):
    stats = rag_stats(Path(root).resolve())
    click.echo(f"chunks={stats.get('chunk_count', 0)} indexed_at={stats.get('indexed_at')}")


@rag_cmd.command("search")
@click.option("--root", default=".", help="项目根目录")
@click.option("--query", required=True, help="检索词")
@click.option("--kinds", default=None, help="逗号分隔过滤")
@click.option("--top", default=12, show_default=True, type=int)
def rag_search_cmd(root, query, kinds, top):
    kind_list = [k.strip() for k in kinds.split(",")] if kinds else None
    hits = rag_search(Path(root).resolve(), query, kinds=kind_list, top=top)
    if not hits:
        click.echo("无命中。")
        return
    for i, h in enumerate(hits, 1):
        click.echo(f"[{i}] {h['kind']} {h['anchor']} ({h['attribution']})")
        click.echo(f"    {h['excerpt'][:200]}...")
