from pathlib import Path

import pytest
import yaml

from nexogenesis.graph.build import rebuild_graph


def _write_card(cards_dir: Path, cid: str, *, title: str, type_: str,
                domains: list[str], relations: list[dict]) -> None:
    meta = {
        "id": cid,
        "title": title,
        "type": type_,
        "maturity": "growing",
        "lifecycle": "active",
        "domains": domains,
        "origin": "user",
        "sources": ["test"],
        "relations": relations,
        "created": "2026-08-08",
        "updated": "2026-08-08",
    }
    text = "---\n" + yaml.safe_dump(meta, allow_unicode=True) + "---\n\n正文。\n"
    (cards_dir / f"{cid}.md").write_text(text, encoding="utf-8")


@pytest.fixture
def kb_root(tmp_path: Path) -> Path:
    """最小知识库：2 个 domain + 3 张卡（含 supports 与 conflicts-with 关系）。"""
    cards_dir = tmp_path / "01-Cards"
    cards_dir.mkdir()
    _write_card(cards_dir, "domain-alpha", title="领域甲", type_="domain",
                domains=["domain-alpha"], relations=[])
    _write_card(cards_dir, "domain-beta", title="领域乙", type_="domain",
                domains=["domain-beta"], relations=[])
    _write_card(cards_dir, "card-a", title="卡片A", type_="claim",
                domains=["domain-alpha"],
                relations=[{"target": "card-b", "type": "supports", "note": ""}])
    _write_card(cards_dir, "card-b", title="卡片B", type_="model",
                domains=["domain-beta"],
                relations=[{"target": "card-a", "type": "conflicts-with", "note": ""}])
    _write_card(cards_dir, "card-c", title="卡片C", type_="conflict",
                domains=["domain-alpha"],
                relations=[{"target": "card-a", "type": "involves", "note": ""},
                           {"target": "card-b", "type": "involves", "note": ""}])
    rebuild_graph(tmp_path)
    return tmp_path
