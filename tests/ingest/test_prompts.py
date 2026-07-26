from pathlib import Path

from nexogenesis.ingest.prompts import render_compile_prompt


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
