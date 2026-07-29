from pathlib import Path

from nexogenesis.ingest.prompts import render_compile_prompt, render_digest_prompt


def test_render_compile_prompt():
    units = [{
        "source_path": Path("a.md"),
        "title": "第一节",
        "section": "第一节",
        "page_range": "",
        "char_count": 10,
        "text": "hello",
    }]
    prompt = render_compile_prompt(units, genre="book")
    assert "hello" in prompt
    assert "阅读窗" in prompt
    assert "1～6" in prompt or "1-6" in prompt
    assert "质料" in prompt


def test_render_digest_prompt_principle_not_hard_ban():
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
    assert "禁止二次摘要掏空" not in prompt
    assert "语义槽" in prompt or "必需语义槽" in prompt
    assert "转入" in prompt or "并入" in prompt or "质料" in prompt
    assert "领域" in prompt
