from nexogenesis.ingest.batch_auto import self_check_batch, suggest_lenses, stamp_approved_by


def test_self_check_digest_requires_consumed():
    data = {
        "operation": {"id": "1", "source": "s", "approved_by": "agent"},
        "writes": [
            {
                "target": "card",
                "id": "a",
                "title": "A",
                "type": "claim",
                "maturity": "seed",
                "lifecycle": "active",
                "domains": ["d"],
                "origin": "document",
                "body": "x",
                "created": "2026-07-24",
                "updated": "2026-07-24",
            }
        ],
    }
    errs = self_check_batch(data, mode="digest", bootstrap=False)
    assert any("consumed_buffers" in e for e in errs)


def test_self_check_bootstrap_domain_first():
    data = {
        "operation": {
            "id": "1",
            "source": "s",
            "approved_by": "agent",
            "consumed_buffers": ["05-Buffer/x.md"],
        },
        "writes": [
            {
                "target": "card",
                "id": "c1",
                "title": "C",
                "type": "claim",
                "maturity": "seed",
                "lifecycle": "active",
                "domains": ["新域"],
                "origin": "document",
                "body": "x",
                "created": "2026-07-24",
                "updated": "2026-07-24",
            }
        ],
    }
    errs = self_check_batch(data, mode="digest", bootstrap=True)
    assert any("domain" in e for e in errs)


def test_suggest_lenses_skips_weak_cross_source():
    signals = {
        "cluster": ["domain `x` 无成员卡片（可能是空壳/标签型）"],
        "distinguish": [],
        "articulate": [],
        "cross_source": ["当前 Buffer 来源较单一；跨源镜头可暂缓或扩大材料后再跑"],
    }
    assert suggest_lenses(signals) == ["cluster"]


def test_stamp_preserves_user(tmp_path):
    p = tmp_path / "batch.yaml"
    p.write_text(
        "operation:\n  id: 1\n  source: s\n  approved_by: user\nwrites: []\n",
        encoding="utf-8",
    )
    assert stamp_approved_by(p, "agent") == "user"
    assert "approved_by: user" in p.read_text(encoding="utf-8")
