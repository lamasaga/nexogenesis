from pathlib import Path

import click

from nexogenesis.graph.analyze import analyze_graph
from nexogenesis.graph.build import load_snapshot, rebuild_graph
from nexogenesis.graph.export import write_graphml
from nexogenesis.graph.retrieve import graph_retrieve


@click.group()
def graph_cmd():
    """结构图索引与检索。"""
    pass


@graph_cmd.command("rebuild")
@click.option("--root", default=".", help="项目根目录")
def graph_rebuild(root: str):
    snap = rebuild_graph(Path(root).resolve())
    click.echo(f"Graph rebuilt: nodes={snap.node_count} edges={snap.edge_count}")


@graph_cmd.command("stats")
@click.option("--root", default=".", help="项目根目录")
def graph_stats(root: str):
    root_path = Path(root).resolve()
    snap = load_snapshot(root_path)
    if not snap:
        click.echo("尚无图索引；请运行 graph rebuild。")
        return
    stats = snap.to_stats_dict()
    click.echo(f"nodes={stats['node_count']} edges={stats['edge_count']}")
    click.echo(f"by_kind={stats.get('edges_by_kind')}")
    click.echo(f"built_at={stats.get('built_at')}")


@graph_cmd.command("analyze")
@click.option("--root", default=".", help="项目根目录")
@click.option("--rebuild", is_flag=True, help="分析前重建图")
def graph_analyze(root: str, rebuild: bool):
    root_path = Path(root).resolve()
    metrics = analyze_graph(root_path, rebuild=rebuild)
    click.echo(
        f"Analyzed: orphans={metrics['orphan_count']} "
        f"conflict_gaps={metrics['conflict_gap_count']} "
        f"bridges={metrics.get('bridge_count', 0)}"
    )
    click.echo(f"Report: {root_path / '.nexogenesis/graph/reports/latest-summary.md'}")
    click.echo(f"Draft: {root_path / '.nexogenesis/tmp/construct/structure-ops-draft.md'}")


@graph_cmd.command("retrieve")
@click.option("--root", default=".", help="项目根目录")
@click.option("--query", default="", help="检索问题")
@click.option("--seed", multiple=True, help="显式种子卡片 id")
@click.option("--hops", default=2, show_default=True, type=int)
@click.option("--max-nodes", default=24, show_default=True, type=int)
@click.option("--out", "out_name", default="graph-context", help="输出文件名（不含扩展名）")
def graph_retrieve_cmd(root, query, seed, hops, max_nodes, out_name):
    from nexogenesis.retrieve.context_package import save_context_package

    root_path = Path(root).resolve()
    result = graph_retrieve(
        root_path,
        query=query,
        seeds=list(seed),
        max_hops=hops,
        max_nodes=max_nodes,
    )
    pkg = {"query": query, "mode": "graph-only", "structure": result, "material": []}
    path = save_context_package(root_path, pkg, name=out_name)
    click.echo(f"status={result.get('status')} nodes={len(result.get('nodes') or [])}")
    click.echo(f"已写入: {path}")


@graph_cmd.command("export")
@click.option("--root", default=".", help="项目根目录")
@click.option("--center", default=None, help="子图中心卡片 id")
@click.option("--hops", default=2, show_default=True, type=int)
@click.option(
    "--out",
    "out_file",
    default=".nexogenesis/tmp/graph/graph.graphml",
    show_default=True,
    help="输出 GraphML 路径（相对 root）",
)
@click.option("--rebuild", is_flag=True, help="导出前重建图")
def graph_export(root, center, hops, out_file, rebuild):
    root_path = Path(root).resolve()
    out_path = root_path / out_file
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_graphml(root_path, out_path, center=center, hops=hops, rebuild=rebuild)
    click.echo(f"GraphML 已写入: {out_path}")
