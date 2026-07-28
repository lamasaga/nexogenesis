from pathlib import Path

import click
import yaml

from nexogenesis.retrieve.context_package import MODES, build_context_package, save_context_package


@click.command()
@click.option("--root", default=".", help="项目根目录")
@click.option("--query", default="", help="检索问题或任务描述")
@click.option(
    "--mode",
    default="talk",
    type=click.Choice(list(MODES), case_sensitive=False),
    show_default=True,
)
@click.option("--seed", multiple=True, help="显式结构种子卡片 id")
@click.option("--budget-chars", default=16000, show_default=True, type=int)
@click.option("--graph-hops", default=2, show_default=True, type=int)
@click.option("--graph-nodes", default=24, show_default=True, type=int)
@click.option("--rag-top", default=None, type=int, help="RAG 块上限（默认随 mode）")
@click.option("--no-graph", is_flag=True, help="禁用图检索")
@click.option("--no-rag", is_flag=True, help="禁用 RAG")
@click.option("--no-attention", is_flag=True, help="禁用双账户注意力组装（回退旧 retrieve）")
@click.option("--no-stm", is_flag=True, help="组装时不读短期记忆")
@click.option("--out", "out_name", default="context", help="输出文件名（不含扩展名）")
@click.option("--print-yaml", is_flag=True, help="同时打印 YAML 到 stdout")
def retrieve_cmd(
    root,
    query,
    mode,
    seed,
    budget_chars,
    graph_hops,
    graph_nodes,
    rag_top,
    no_graph,
    no_rag,
    no_attention,
    no_stm,
    out_name,
    print_yaml,
):
    root_path = Path(root).resolve()
    pkg = build_context_package(
        root_path,
        query=query,
        mode=mode.lower(),
        seeds=list(seed),
        budget_chars=budget_chars,
        graph_hops=graph_hops,
        graph_nodes=graph_nodes,
        rag_top=rag_top,
        use_graph=not no_graph,
        use_rag=not no_rag,
        use_attention=not no_attention,
        use_stm=not no_stm,
    )
    path = save_context_package(root_path, pkg, name=out_name)
    click.echo(
        f"status={pkg.get('status')} "
        f"structure_nodes={pkg['budget']['structure_nodes']} "
        f"rag_chunks={pkg['budget']['rag_chunks']}"
    )
    accounts = (pkg.get("structure") or {}).get("accounts") or {}
    if accounts:
        click.echo(
            f"accounts core={len(accounts.get('core') or [])} "
            f"expansion={len(accounts.get('expansion') or [])} "
            f"conflict={len(accounts.get('conflict') or [])}"
        )
    if pkg.get("blind_spots"):
        for b in pkg["blind_spots"]:
            click.echo(f"NOTE: {b}")
    click.echo(f"已写入: {path}")
    if print_yaml:
        click.echo(yaml.safe_dump(pkg, allow_unicode=True, sort_keys=False))
