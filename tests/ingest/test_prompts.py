from pathlib import Path

from nexogenesis.ingest.prompts import render_compile_prompt, render_digest_prompt


def test_render_compile_prompt():
    units = [{
        "source_path": Path("a.md"),
        "title": "a",
        "section": "",
        "page_range": "",
        "char_count": 10,
        "text": "hello",
    }]
    prompt = render_compile_prompt(units, genre="essay")
    assert "hello" in prompt
    assert "meaning-unit" in prompt
    assert "role" in prompt
    assert "合格示例" in prompt
    assert "意义切片" in prompt or "快节奏" in prompt
    assert "不要求" in prompt  # 明确不强制四级槽
    assert "不要写" in prompt or "Harness" in prompt


def test_render_digest_prompt_separates_domain_skeleton():
    prompt = render_digest_prompt(
        buffers=[{"role": "meaning-unit", "title": "t", "path": "05-Buffer/x.md", "text": "---\nt\n"}],
        catalog=[
            {"type": "domain", "line": "- 教学 (domain) 教学领域"},
            {"type": "claim", "line": "- 反馈 (claim) 反馈主张"},
        ],
        deep_cards=[
            {"id": "教学", "type": "domain", "title": "教学领域", "domains": [], "body": "骨架"},
            {"id": "反馈", "type": "claim", "title": "反馈主张", "domains": ["教学"], "body": "实例"},
        ],
        questions=[],
    )
    assert "领域骨架" in prompt or "领域卡片目录" in prompt
    assert "滋养" in prompt or "v3.1" in prompt
    assert "enrich" in prompt.lower() or "丰富" in prompt
