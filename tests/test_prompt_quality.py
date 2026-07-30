"""Prompt 质量覆盖测试：确保 prompts 包含足够的操作化引导。"""

from nexogenesis.ingest.prompts import _load_template


GENRES = ["book", "paper", "essay", "dialogue", "scrap", "generic"]


def test_compile_prompts_contain_extraction_dimensions():
    """每个 compile prompt 都应要求原文摘录/锚点，并给出体裁特定的提取维度。"""
    for genre in GENRES:
        template = _load_template(f"compile-{genre}")
        text = template.render(units=[], format_rules="", deep=False)
        assert "quote" in text or "摘录" in text, f"{genre} prompt 缺少 quote/摘录 要求"
        assert (
            "机制" in text
            or "主张" in text
            or "立场" in text
            or "维度" in text
        ), f"{genre} prompt 缺少提取维度信号"


def test_compile_prompts_forbid_empty_slices():
    """compile prompt 应禁止空心摘要或硬凑碎片。"""
    for genre in GENRES:
        template = _load_template(f"compile-{genre}")
        text = template.render(units=[], format_rules="", deep=False)
        assert (
            "空摘要" in text
            or "硬造" in text
            or "硬拆" in text
            or "薄片" in text
            or "质料" in text
        ), f"{genre} prompt 缺少禁止空切片/硬凑的提示"


def test_digest_prompt_contains_decision_tree():
    """digest prompt 应包含明确的决策树信号。"""
    template = _load_template("digest")
    text = template.render(buffers=[], catalog=[], deep_cards=[])
    assert "是否已有" in text, "digest prompt 缺少「是否已有同主题 Card」判断"
    assert "新建" in text, "digest prompt 缺少「新建 Card」动作"
    assert "enrich" in text, "digest prompt 缺少「enrich」动作"
    assert "skip" in text, "digest prompt 缺少「skip」动作"


def test_digest_prompt_mentions_profile_update():
    """digest prompt 应提示更新领域 Profile。"""
    template = _load_template("digest")
    text = template.render(buffers=[], catalog=[], deep_cards=[])
    assert "profile_field" in text, "digest prompt 缺少 profile_field 更新入口"
    assert "领域理念" in text, "digest prompt 未提及领域理念"
    assert "领域思维模型" in text, "digest prompt 未提及领域思维模型"


def test_construct_prompt_contains_lens_checklist():
    """construct prompt 应包含四个镜头职责。"""
    template = _load_template("construct")
    text = template.render(catalog=[], deep_cards=[], signals=[], lens="cluster")
    assert "cluster" in text, "construct prompt 缺少 cluster 镜头"
    assert "distinguish" in text, "construct prompt 缺少 distinguish 镜头"
    assert "articulate" in text, "construct prompt 缺少 articulate 镜头"
    assert "cross_source" in text, "construct prompt 缺少 cross_source 镜头"


def test_construct_prompt_forbids_bulk_creation():
    """construct prompt 应强调原则上不新建 Card。"""
    template = _load_template("construct")
    text = template.render(catalog=[], deep_cards=[], signals=[], lens="cluster")
    assert "不新建" in text, "construct prompt 未禁止大量新建 Card"
    assert "digest 阶段" in text, "construct prompt 未区分与 digest 的边界"


def test_construct_diagnose_has_checklist_signals():
    """construct-diagnose prompt 应给每个镜头具体检查信号。"""
    template = _load_template("construct-diagnose")
    text = template.render(catalog=[], buffers=[], signals=[], questions=[])
    assert "orphan" in text or "空壳 domain" in text, "cluster 镜头缺少具体信号"
    assert "conflict 缺 involves" in text or "互相否定" in text, "distinguish 镜头缺少具体信号"
    assert "高频术语" in text or "关系团" in text, "articulate 镜头缺少具体信号"
    assert "多源互补" in text or "跨源对立" in text, "cross_source 镜头缺少具体信号"


def test_evaluation_fixtures_exist():
    """评估集文件应存在，并覆盖 7 种卡片类型。"""
    from pathlib import Path

    root = Path(__file__).resolve().parent / "evaluation"
    assert (root / "compile_samples" / "book_excerpt.md").exists()
    assert (root / "compile_samples" / "paper_excerpt.md").exists()
    assert (root / "compile_samples" / "essay_excerpt.md").exists()
    assert (root / "digest_samples" / "sample_buffers.yaml").exists()

    gold_cards = [
        "domain-制度经济学.md",
        "claim-可操作反馈.md",
        "claim-反条件原则.md",
        "phenomenon-旧关系网络资源配置.md",
        "model-制度摩擦.md",
        "method-可操作反馈实验.md",
        "entity-俄罗斯私营企业家.md",
        "conflict-事后解释与反条件.md",
    ]
    for name in gold_cards:
        assert (root / "gold_cards" / name).exists(), f"缺少 gold card: {name}"
