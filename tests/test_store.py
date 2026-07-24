from pathlib import Path

import pytest

from nexogenesis.store import Store


@pytest.fixture
def fixture_store(tmp_path: Path):
    import shutil

    src = Path(__file__).parent / "fixtures"
    dst = tmp_path / "cards"
    shutil.copytree(src, dst)
    return Store(dst).load()


def test_load_cards(fixture_store: Store):
    assert "feedback-gap-actionable" in fixture_store.cards
    assert "feedback-gap-actionable" in fixture_store.by_domain["teaching"]


def test_validate_ok(fixture_store: Store):
    errors, warnings = fixture_store.validate()
    assert errors == []
