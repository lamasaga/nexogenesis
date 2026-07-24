from pathlib import Path

import click

from nexogenesis.store import Store
from nexogenesis.yaml_utils import atomic_write_file


def render_domain_index(store: Store) -> str:
    lines = ["# 领域索引（自动生成）\n"]
    for domain, ids in sorted(store.by_domain.items()):
        domain_card = store.cards.get(domain)
        title = domain_card.title if domain_card else domain
        lines.append(f"## {title} (`{domain}`)\n")
        for cid in sorted(ids):
            if cid == domain:
                continue
            card = store.cards[cid]
            lines.append(f"- [[{cid}|{card.title}]] ({card.type.value})")
        lines.append("")
    return "\n".join(lines)


def render_conflict_index(store: Store) -> str:
    lines = ["# 冲突索引（自动生成）\n"]
    for cid, card in sorted(store.cards.items()):
        if card.type.value != "conflict":
            continue
        lines.append(f"## [[{cid}|{card.title}]]")
        involved = [r.target for r in card.relations if r.type.value == "involves"]
        lines.append(f"涉及：{', '.join(involved)}\n")
    return "\n".join(lines)


def render_theory_index(store: Store) -> str:
    lines = ["# 理论索引（自动生成）\n"]
    for cid in sorted(store.theories):
        card = store.cards[cid]
        lines.append(f"- [[{cid}|{card.title}]] ({card.type.value}, {card.theory_status})")
    return "\n".join(lines)


def generate_indexes(root_path: Path) -> None:
    meta_dir = root_path / "01-Cards" / "_meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    store = Store(root_path / "01-Cards").load()
    atomic_write_file(meta_dir / "domain-index.md", render_domain_index(store))
    atomic_write_file(meta_dir / "conflict-index.md", render_conflict_index(store))
    atomic_write_file(meta_dir / "theory-index.md", render_theory_index(store))


@click.command()
@click.option("--root", default=".", help="项目根目录")
def index_cmd(root: str):
    generate_indexes(Path(root).resolve())
    click.echo("Indexes regenerated.")
