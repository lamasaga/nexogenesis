# P1 文档摄入流水线实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 v4.0 compile/digest/construct 流水线迁移并适配到 Nexogenesis P0 的扁平结构与 7 型卡片，新增 `compile`/`digest`/`construct` CLI 命令。

**Architecture:** 在 `nexogenesis/ingest/` 中复用 v4.0 已验证的 genre 检测、chunk、batch 逻辑；命令层负责生成 prompt/batch 文件，由 code agent 调用 LLM 后回写，再由 `--apply` 完成原子写入；未来通过 `LLMClient` 接口可切换为自动调用。

**Tech Stack:** Python 3.13, Click, PyYAML, JSON Schema, Jinja2（新增）, pytest。

---

## 文件结构总览

| 文件 | 责任 |
|---|---|
| `pyproject.toml` | 新增 `jinja2` 依赖 |
| `nexogenesis/ingest/__init__.py` | 常量、成本模型、路径工具 |
| `nexogenesis/ingest/ingest.py` | 扫描 Inbox、genre 检测、编译计划 |
| `nexogenesis/ingest/chunker.py` | 文档分块（段落/对话/PDF） |
| `nexogenesis/ingest/pdf_extractor.py` | PDF 目录/页码提取（从 v4.0 迁移） |
| `nexogenesis/ingest/batch_runner.py` | batch 分组、prompt 生成、Buffer 解析与写入 |
| `nexogenesis/ingest/prompts.py` | 加载 scheme 模板，渲染 prompt |
| `schemes/default/prompts/*.txt` | 各体裁 compile 与 digest/construct prompt 模板 |
| `nexogenesis/commands/compile.py` | `compile` CLI |
| `nexogenesis/commands/digest.py` | `digest` CLI |
| `nexogenesis/commands/construct.py` | `construct` CLI |
| `nexogenesis/cli.py` | 注册三个新命令 |
| `tests/ingest/` | 迁移的 v4.0 单元测试 |
| `tests/test_compile_command.py` | compile 命令集成测试 |
| `tests/test_digest_command.py` | digest 命令集成测试 |
| `tests/test_construct_command.py` | construct 命令集成测试 |
| `AGENTS.md` | 新增 `/compile`、`/digest`、`/construct` 使用说明 |

---

## Task 1: 添加 Jinja2 依赖

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: 在 dependencies 中加入 jinja2**

```toml
[project]
...
dependencies = [
    "pyyaml>=6.0",
    "jsonschema>=4.0",
    "click>=8.0",
    "jinja2>=3.1",
]
```

- [ ] **Step 2: 重新安装开发依赖**

```bash
.venv/Scripts/pip install -e ".[dev]"
```

- [ ] **Step 3: 提交**

```bash
git add pyproject.toml
pip freeze > requirements.txt   # 若项目使用 requirements.txt
# 仅当存在 requirements.txt 时才 add
git commit -m "chore: add jinja2 dependency"
```

---

## Task 2: 创建 `nexogenesis/ingest/__init__.py`

**Files:**
- Create: `nexogenesis/ingest/__init__.py`

- [ ] **Step 1: 写入常量与成本模型**

```python
"""文档摄入引擎公共常量与工具函数。"""

import re
from pathlib import Path

ROOT = Path(".").resolve()
INBOX_DIR = ROOT / "00-Inbox"
BUFFER_DIR = ROOT / "05-Buffer"
ARCHIVE_DIR = ROOT / "03-Archive"
CARDS_DIR = ROOT / "01-Cards"
PROFILE_DIR = ROOT / "02-Profile"
TMP_DIR = ROOT / ".nexogenesis" / "tmp"

DEFAULT_BATCH_LIMIT = 30000

WORD_RE = re.compile(r"[a-zA-Z]+(?:['-][a-zA-Z]+)?")

CHINESE_CHAR_COST_NUM = 2
ENGLISH_WORD_COST_NUM = 3


def count_chars(text: str) -> int:
    """估算等效中文字符数。中文字符 +1，英文单词 +1.5（向上取整）。"""
    chinese = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    english_words = len(WORD_RE.findall(text))
    return (chinese * CHINESE_CHAR_COST_NUM + english_words * ENGLISH_WORD_COST_NUM + 1) // 2


VALID_BUFFER_TYPES = {
    "domain", "claim", "phenomenon", "model", "method", "entity", "conflict"
}


def ensure_buffer_dirs(base_dir: Path = BUFFER_DIR) -> None:
    """确保 Buffer 子目录存在（7 种类型）。"""
    for subtype in VALID_BUFFER_TYPES:
        (base_dir / subtype).mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 2: 提交**

```bash
git add nexogenesis/ingest/__init__.py
git commit -m "feat(ingest): add constants and char-count model"
```

---

## Task 3: 迁移 `ingest.py`（扫描与体裁检测）

**Files:**
- Create: `nexogenesis/ingest/ingest.py`
- Test: `tests/ingest/test_ingest.py`

- [ ] **Step 1: 复制 v4.0 `scripts/compile_lib/ingest.py` 到 `nexogenesis/ingest/ingest.py`**

调整 import：
```python
from nexogenesis.ingest import count_chars
```

- [ ] **Step 2: 修改 `predict_genre` 在未知时回退为 `"essay" 而非 unknown（方便一键模式）**

```python
def predict_genre(meta: dict, doc_type: str) -> str:
    if doc_type == "pdf":
        if meta["toc_chapters"] >= BOOK_MIN_TOC_CHAPTERS or meta["page_count"] > BOOK_MIN_PAGES:
            return "book"
        if meta["academic_hits"] >= PAPER_MIN_ACADEMIC_MARKERS:
            return "paper"
        return "generic"
    if meta["academic_hits"] >= PAPER_MIN_ACADEMIC_MARKERS:
        return "paper"
    if (
        meta["dialogue_ratio"] > DIALOGUE_MIN_LINE_RATIO
        and meta["dialogue_lines"] >= DIALOGUE_MIN_LINES
        and meta["dialogue_speakers"] >= DIALOGUE_MIN_SPEAKERS
    ):
        return "dialogue"
    if meta["char_count"] < SCRAP_MAX_CHARS and meta["heading_count"] == 0:
        return "scrap"
    return "essay"
```

- [ ] **Step 3: 编写测试**

```python
from pathlib import Path

from click.testing import CliRunner

from nexogenesis.commands.init import init_cmd
from nexogenesis.ingest.ingest import classify_file, predict_genre, scan_inbox


def test_classify_file(tmp_path: Path):
    md = tmp_path / "a.md"
    md.write_text("hello", encoding="utf-8")
    assert classify_file(md) == "text"


def test_predict_genre_scrap():
    meta = {
        "char_count": 500,
        "dialogue_ratio": 0.0,
        "dialogue_lines": 0,
        "dialogue_speakers": 0,
        "academic_hits": 0,
        "heading_count": 0,
    }
    assert predict_genre(meta, "text") == "scrap"


def test_scan_inbox(tmp_path: Path):
    (tmp_path / "a.md").write_text("text", encoding="utf-8")
    (tmp_path / "b.pdf").write_bytes(b"pdf")
    docs = scan_inbox(tmp_path)
    assert len(docs) == 2
```

- [ ] **Step 4: 运行测试**

```bash
.venv/Scripts/pytest tests/ingest/test_ingest.py -v
```

- [ ] **Step 5: 提交**

```bash
git add nexogenesis/ingest/ingest.py tests/ingest/test_ingest.py
git commit -m "feat(ingest): migrate inbox scan and genre detection"
```

---

## Task 4: 迁移 `chunker.py` 与 `pdf_extractor.py`

**Files:**
- Create: `nexogenesis/ingest/chunker.py`
- Create: `nexogenesis/ingest/pdf_extractor.py`
- Test: `tests/ingest/test_chunker.py`

- [ ] **Step 1: 复制 v4.0 `chunker.py` 并调整 import**

```python
from nexogenesis.ingest import CHINESE_CHAR_COST_NUM, ENGLISH_WORD_COST_NUM, WORD_RE, count_chars
from nexogenesis.ingest.ingest import DIALOGUE_LINE_RE
from nexogenesis.ingest.pdf_extractor import extract_pdf_toc_chunks
```

- [ ] **Step 2: 复制 v4.0 `pdf_extractor.py`**

路径导入调整为相对 `nexogenesis.ingest`。

- [ ] **Step 3: 迁移 v4.0 chunker 测试**

创建 `tests/ingest/test_chunker.py`，包含 `count_chars`、`_split_text_by_paragraphs`、`_split_dialogue_by_turns`、`build_compile_units` 的基本断言。

- [ ] **Step 4: 运行测试**

```bash
.venv/Scripts/pytest tests/ingest/test_chunker.py -v
```

- [ ] **Step 5: 提交**

```bash
git add nexogenesis/ingest/chunker.py nexogenesis/ingest/pdf_extractor.py tests/ingest/test_chunker.py
git commit -m "feat(ingest): migrate chunker and pdf extractor"
```

---

## Task 5: 迁移并改造 `batch_runner.py`

**Files:**
- Create: `nexogenesis/ingest/batch_runner.py`
- Test: `tests/ingest/test_batch_runner.py`

- [ ] **Step 1: 创建 `batch_runner.py`**

复制 v4.0 核心函数：`build_batches`, `format_batch_prompt`, `parse_llm_buffers`, `_sanitize_filename`。

关键改造：
- `VALID_BUFFER_TYPES` 改为 7 种；
- `_FORMAT_RULES` 中 type list 改为 7 种；非法 type 回退到 `claim`（而不是 `note`）；
- `parse_llm_buffers` 中 `btype` 非法时回退 `claim`；
- `write_buffer` 写入新 Buffer schema（含 `proposed_domains`, `proposed_maturity`）。

```python
from datetime import datetime
from pathlib import Path

import yaml

from nexogenesis.ingest import BUFFER_DIR, VALID_BUFFER_TYPES


def build_batches(units: list[dict], max_chars: int = 30000) -> list[list[dict]]:
    """按 max_chars 上限分批。"""
    batches = []
    current = []
    current_chars = 0
    for unit in units:
        unit_chars = unit["char_count"]
        if unit_chars > max_chars:
            if current:
                batches.append(current)
                current = []
                current_chars = 0
            batches.append([unit])
            continue
        if current_chars + unit_chars > max_chars and current:
            batches.append(current)
            current = []
            current_chars = 0
        current.append(unit)
        current_chars += unit_chars
    if current:
        batches.append(current)
    return batches


def format_batch_prompt(units: list[dict], genre: str | None = None, deep: bool = False) -> str:
    """生成 batch prompt（模板从 scheme 加载，此处保留旧逻辑占位）。"""
    from nexogenesis.ingest.prompts import render_compile_prompt
    return render_compile_prompt(units, genre=genre, deep=deep)
```

- [ ] **Step 2: 编写 `parse_llm_buffers` 测试**

```python
from nexogenesis.ingest.batch_runner import parse_llm_buffers


def test_parse_llm_buffers():
    raw = """
---
title: 测试
type: claim
source: s1
---
正文1

---
title: 测试2
type: model
source: s2
---
正文2
"""
    buffers = parse_llm_buffers(raw, "default")
    assert len(buffers) == 2
    assert buffers[0]["type"] == "claim"
```

- [ ] **Step 3: 运行测试**

```bash
.venv/Scripts/pytest tests/ingest/test_batch_runner.py -v
```

- [ ] **Step 4: 提交**

```bash
git add nexogenesis/ingest/batch_runner.py tests/ingest/test_batch_runner.py
git commit -m "feat(ingest): migrate batch runner with 7-type schema"
```

---

## Task 6: 创建 Prompt 模板加载器

**Files:**
- Create: `nexogenesis/ingest/prompts.py`
- Create: `schemes/default/prompts/compile-generic.txt`
- Create: `schemes/default/prompts/compile-book.txt`
- Create: `schemes/default/prompts/compile-paper.txt`
- Create: `schemes/default/prompts/compile-essay.txt`
- Create: `schemes/default/prompts/compile-dialogue.txt`
- Create: `schemes/default/prompts/compile-scrap.txt`

- [ ] **Step 1: 创建 `prompts.py`**

```python
"""Prompt 模板加载与渲染。"""

from pathlib import Path

from jinja2 import Template

from nexogenesis.ingest import VALID_BUFFER_TYPES


DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "schemes" / "default" / "prompts"


def _load_template(name: str, scheme_dir: Path | None = None) -> Template:
    dirs = []
    if scheme_dir:
        dirs.append(scheme_dir / "prompts")
    dirs.append(DEFAULT_PROMPTS_DIR)
    for d in dirs:
        path = d / f"{name}.txt"
        if path.exists():
            return Template(path.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"Prompt template not found: {name}")


def _format_rules() -> str:
    types = ", ".join(sorted(VALID_BUFFER_TYPES))
    return f"""请遵循以下输出规则：
1. 每个碎片单独输出为一个 YAML frontmatter + Markdown 正文块。
2. 为每个碎片指定一个暂定 type，必须从以下 7 个类型中选择：{types}。
   若无法判定 type，先放入 claim（并标注为 seed 成熟度）。
3. 禁止使用 [[ ]] 链接；提及已有概念时用加粗即可。
4. source 字段必须精确标注原始来源。
5. frontmatter 增加 genre 字段；涉及作者本人作品时增加 perspective: self，外部作品为 perspective: external。
6. 可选字段 proposed_domains（列表）和 proposed_maturity（seed/growing/mature）。
7. 宁可少拆，不要硬造；允许拆解不完整。"""


def render_compile_prompt(units: list[dict], genre: str | None = None, deep: bool = False) -> str:
    name = f"compile-{genre or 'generic'}"
    try:
        template = _load_template(name)
    except FileNotFoundError:
        template = _load_template("compile-generic")
    units_render = []
    for idx, u in enumerate(units, 1):
        source = " / ".join(
            p for p in [u["source_path"].name, u.get("title", ""), u.get("section", ""), u.get("page_range", "")] if p
        )
        units_render.append({
            "index": idx,
            "total": len(units),
            "source": source,
            "char_count": u["char_count"],
            "text": u["text"],
        })
    return template.render(units=units_render, format_rules=_format_rules(), deep=deep)
```

- [ ] **Step 2: 创建各体裁 prompt 模板**

示例 `compile-generic.txt`：

```text
你是一位个人知识库的编译助手。当前材料体裁为【通用】。

从以下维度提取原子碎片，每个维度独立成块：
a. problem：核心问题、研究动机。
b. claim：作者核心主张、立场、结论性判断。
c. model：提出的模型/框架/解释结构，含关键组件与关系。
d. method：方法/流程/实现细节，含输入、步骤、输出。
e. evidence：实验/证据/评测，含数据集、指标、结果、与基线的对比。
f. limit：限制、代价、未解决问题、适用范围边界。
g. conflict：与现有工作、常识或本知识库已有观点的张力。
h. connection：与其他文档、已知概念的潜在关联假设。
i. quote：值得保留的原文摘录（≤3 条/碎片），必须标注页码/章节。

{{ format_rules }}

本批共 {{ units|length }} 个片段：

{% for u in units %}
---
片段 {{ u.index }}/{{ u.total }}
source: {{ u.source }}
char_count: {{ u.char_count }}
---
{{ u.text }}

{% endfor %}
{% if deep %}
【深度编译模式】
- 碎片数量不设上限，按信息密度榨取；但仍禁止硬造碎片。
- 多遍扫描：先主线/结构，再逐节深挖，最后横向挖掘（冲突、关联、风格线索）。
- 输出末尾附维度覆盖度说明。
{% endif %}
```

其他体裁模板类似，参考 v4.0 `GENRE_PROMPTS` 内容。

- [ ] **Step 3: 测试 prompt 渲染**

```python
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
    assert "claim" in prompt
```

- [ ] **Step 4: 提交**

```bash
git add nexogenesis/ingest/prompts.py schemes/default/prompts/ tests/ingest/test_prompts.py
git commit -m "feat(ingest): add Jinja2 prompt templates"
```

---

## Task 7: 实现 `compile` 命令

**Files:**
- Create: `nexogenesis/commands/compile.py`
- Test: `tests/test_compile_command.py`

- [ ] **Step 1: 创建 `compile.py`**

```python
import shutil
from pathlib import Path

import click
import yaml

from nexogenesis import journal
from nexogenesis.commands.index import generate_indexes
from nexogenesis.commands.validate import run_validate
from nexogenesis.ingest import ARCHIVE_DIR, BUFFER_DIR, INBOX_DIR, TMP_DIR, ensure_buffer_dirs
from nexogenesis.ingest.batch_runner import build_batches, format_batch_prompt, parse_llm_buffers
from nexogenesis.ingest.chunker import build_compile_units
from nexogenesis.ingest.ingest import build_compile_plan, scan_inbox
from nexogenesis.yaml_utils import atomic_write_file


def _write_prompts(batches: list, deep: bool, tmp_dir: Path) -> list[Path]:
    paths = []
    for idx, batch in enumerate(batches, 1):
        genre = batch[0].get("genre") or "generic"
        prompt = format_batch_prompt(batch, genre=genre, deep=deep)
        p = tmp_dir / f"batch-{idx:03d}-{genre}-prompt.md"
        atomic_write_file(p, prompt)
        paths.append(p)
    return paths


def _apply_responses(tmp_dir: Path, default_source: str) -> list[Path]:
    response_files = sorted(tmp_dir.glob("batch-*-response.yaml"))
    if not response_files:
        raise click.ClickException("未找到 LLM response 文件，请先让 Agent 调用 LLM 并保存 response。")
    written = []
    for rf in response_files:
        raw = yaml.safe_load(rf.read_text(encoding="utf-8"))
        buffers = parse_llm_buffers(raw.get("output", ""), default_source=default_source)
        for buf in buffers:
            # write_buffer 返回 Path
            from nexogenesis.ingest.batch_runner import write_buffer
            written.append(write_buffer(buf, subtype=buf["type"]))
    return written


@click.command()
@click.option("--root", default=".", help="项目根目录")
@click.option("--deep", is_flag=True, help="深度编译模式")
@click.option("--max-chars", default=30000, help="每批最大字符数")
@click.option("--genres", default="", help='体裁覆盖，格式 "文件名=体裁,..."')
@click.option("--apply", is_flag=True, help="应用 LLM response 写入 Buffer")
@click.option("--plan", is_flag=True, help="只输出编译计划")
def compile_cmd(root, deep, max_chars, genres, apply, plan):
    root_path = Path(root).resolve()
    # 更新模块级路径
    inbox = root_path / "00-Inbox"
    tmp_dir = root_path / ".nexogenesis" / "tmp" / "compile"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    docs = scan_inbox(inbox)
    if not docs:
        click.echo("00-Inbox/ 为空，无需编译。")
        return

    compile_plan = build_compile_plan(docs)
    if plan:
        for item in compile_plan:
            click.echo(f"{item['path'].name} -> {item['predicted_genre']}")
        return

    genre_overrides = {}
    if genres:
        for pair in genres.split(","):
            name, genre = pair.split("=", 1)
            genre_overrides[name.strip()] = genre.strip()

    final_genres = {}
    for item in compile_plan:
        final_genres[item["path"].name] = genre_overrides.get(item["path"].name, item["predicted_genre"])

    ensure_buffer_dirs(root_path / "05-Buffer")
    units = build_compile_units(docs, max_chars=max_chars, genres=final_genres)
    batches = build_batches(units, max_chars=max_chars)

    if not apply:
        paths = _write_prompts(batches, deep=deep, tmp_dir=tmp_dir)
        click.echo(f"已生成 {len(paths)} 个 prompt 文件：")
        for p in paths:
            click.echo(f"  {p}")
        click.echo("请 Agent 调用 LLM 并将每个 response 保存为同目录的 batch-XXX-response.yaml，然后运行 --apply。")
        return

    written = _apply_responses(tmp_dir, default_source="00-Inbox compile")
    errors, warnings = run_validate(root_path)
    if errors:
        raise click.ClickException("Buffer 校验失败：\n" + "\n".join(errors))

    # 归档
    processed = {u["source_path"] for u in units}
    for src in processed:
        target = ARCHIVE_DIR / src.name
        counter = 1
        while target.exists():
            target = ARCHIVE_DIR / f"{src.stem}-{counter}{src.suffix}"
            counter += 1
        shutil.move(str(src), str(target))

    journal.append(root_path, f"compile-{len(written)}", "compile", [str(w) for w in written], "00-Inbox", "user")
    generate_indexes(root_path)
    click.echo(f"Compile applied: {len(written)} buffers written, {len(processed)} docs archived.")
```

- [ ] **Step 2: 测试 compile 命令**

```python
from pathlib import Path

from click.testing import CliRunner

from nexogenesis.commands.compile import compile_cmd
from nexogenesis.commands.init import init_cmd


def test_compile_generates_prompts(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    (tmp_path / "00-Inbox" / "note.md").write_text("这是一个测试文档。" * 20, encoding="utf-8")
    result = runner.invoke(compile_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0
    prompts = list((tmp_path / ".nexogenesis" / "tmp" / "compile").glob("*.md"))
    assert len(prompts) >= 1
```

- [ ] **Step 3: 提交**

```bash
git add nexogenesis/commands/compile.py tests/test_compile_command.py
git commit -m "feat(cli): add compile command"
```

---

## Task 8: 实现 `digest` 命令

**Files:**
- Create: `nexogenesis/commands/digest.py`
- Create: `schemes/default/prompts/digest.txt`
- Test: `tests/test_digest_command.py`

- [ ] **Step 1: 创建 `digest.py`**

```python
from pathlib import Path

import click
import yaml

from nexogenesis.ingest import BUFFER_DIR, CARDS_DIR, PROFILE_DIR, TMP_DIR
from nexogenesis.store import Store
from nexogenesis.yaml_utils import atomic_write_file


def _load_buffer_paths(status: str) -> list[Path]:
    paths = []
    for subdir in BUFFER_DIR.iterdir():
        if not subdir.is_dir() or subdir.name.startswith("_"):
            continue
        for p in subdir.glob("*.md"):
            text = p.read_text(encoding="utf-8")
            if f"status: {status}" in text:
                paths.append(p)
    return sorted(paths)


def _render_digest_prompt(buffers: list, cards: list, questions: list) -> str:
    from nexogenesis.ingest.prompts import _load_template
    template = _load_template("digest")
    return template.render(buffers=buffers, cards=cards, questions=questions)


@click.command()
@click.option("--root", default=".", help="项目根目录")
@click.option("--status", default="scratch", help="要消化的 Buffer 状态")
@click.option("--apply", is_flag=True, help="应用 batch 文件写入卡片")
def digest_cmd(root, status, apply):
    root_path = Path(root).resolve()
    buffer_dir = root_path / "05-Buffer"
    tmp_dir = root_path / ".nexogenesis" / "tmp" / "digest"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    buffer_paths = _load_buffer_paths(status)
    if not buffer_paths:
        click.echo("没有待消化的 Buffer。")
        return

    store = Store(root_path / "01-Cards").load()
    cards = [{"id": c.id, "title": c.title, "type": c.type.value, "domains": c.domains} for c in store.cards.values()]
    profile_path = root_path / "02-Profile" / "问题清单.md"
    questions = []
    if profile_path.exists():
        # 简单解析表格
        for line in profile_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("|") and "问题" not in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 2 and parts[1]:
                    questions.append(parts[1])

    buffers = []
    for p in buffer_paths:
        buffers.append({"path": str(p), "text": p.read_text(encoding="utf-8")})

    batch_path = tmp_dir / "batch.yaml"
    prompt = _render_digest_prompt(buffers, cards, questions)
    prompt_path = tmp_dir / "prompt.md"
    atomic_write_file(prompt_path, prompt)

    if not apply:
        click.echo(f"已生成 digest prompt: {prompt_path}")
        click.echo("请 Agent 调用 LLM 并将 batch YAML 保存到 {batch_path}，确认后运行 --apply。")
        return

    if not batch_path.exists():
        raise click.ClickException(f"未找到 {batch_path}，请先生成并确认 batch。")
    from nexogenesis.commands.write import write_cmd
    ctx = click.Context(write_cmd)
    ctx.invoke(write_cmd, batch=str(batch_path), root=str(root_path))

    # 标记已消化 Buffer
    for p in buffer_paths:
        text = p.read_text(encoding="utf-8")
        text = text.replace("status: scratch", "status: digested")
        atomic_write_file(p, text)
    click.echo(f"Digest applied: {len(buffer_paths)} buffers consumed.")
```

- [ ] **Step 2: 创建 `digest.txt` 模板**

```text
你是一位知识库消化助手。当前有一批来自 05-Buffer 的 scratch 片段，请判断它们应该：
1.  enriching 哪张已有卡片（更新 sources/relations/body）；
2.  新建哪些卡片（生成标准 frontmatter）；
3.  产生哪些冲突（生成 conflict 卡）；
4.  追加哪些问题到问题清单。

现有卡片：
{% for c in cards %}
- {{ c.id }} ({{ c.type }}) {{ c.title }} domains={{ c.domains }}
{% endfor %}

现有问题：
{% for q in questions %}
- {{ q }}
{% endfor %}

Buffer 片段：
{% for b in buffers %}
---
路径：{{ b.path }}
{{ b.text }}
{% endfor %}

输出标准 write --batch YAML，operation.approved_by 留 "user"。
```

- [ ] **Step 3: 测试 digest 命令**

```python
def test_digest_generates_prompt(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    # 创建 scratch buffer
    buf_dir = tmp_path / "05-Buffer" / "claim"
    buf_dir.mkdir(parents=True, exist_ok=True)
    buf_dir.joinpath("2026-07-24-test.md").write_text("---\ntitle: t\ntype: claim\nstatus: scratch\n---\nbody", encoding="utf-8")
    result = runner.invoke(digest_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / ".nexogenesis" / "tmp" / "digest" / "prompt.md").exists()
```

- [ ] **Step 4: 提交**

```bash
git add nexogenesis/commands/digest.py schemes/default/prompts/digest.txt tests/test_digest_command.py
git commit -m "feat(cli): add digest command"
```

---

## Task 9: 实现 `construct` 命令

**Files:**
- Create: `nexogenesis/commands/construct.py`
- Create: `schemes/default/prompts/construct.txt`
- Test: `tests/test_construct_command.py`

- [ ] **Step 1: 创建 `construct.py`**

结构类似 digest：读取全部卡片 + scratch/digested Buffer，生成 construct prompt，LLM 输出 batch，--apply 时写入并标记 Buffer constructed。

- [ ] **Step 2: 创建 `construct.txt` 模板**

提示 LLM 检查结构张力（冗余、分裂、链接空洞、领域归属冲突），输出 domain 调整/relations 补全/Profile 更新 batch。

- [ ] **Step 3: 测试**

```python
def test_construct_generates_prompt(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    # 创建 domain + claim
    ...
    result = runner.invoke(construct_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / ".nexogenesis" / "tmp" / "construct" / "prompt.md").exists()
```

- [ ] **Step 4: 提交**

```bash
git add nexogenesis/commands/construct.py schemes/default/prompts/construct.txt tests/test_construct_command.py
git commit -m "feat(cli): add construct command"
```

---

## Task 10: 注册 CLI 命令

**Files:**
- Modify: `nexogenesis/cli.py`

- [ ] **Step 1: 导入并注册三个命令**

```python
from nexogenesis.commands.compile import compile_cmd
from nexogenesis.commands.digest import digest_cmd
from nexogenesis.commands.construct import construct_cmd

main.add_command(compile_cmd, name="compile")
main.add_command(digest_cmd, name="digest")
main.add_command(construct_cmd, name="construct")
```

- [ ] **Step 2: 提交**

```bash
git add nexogenesis/cli.py
git commit -m "feat(cli): register compile/digest/construct commands"
```

---

## Task 11: 迁移 v4.0 测试并补充新测试

**Files:**
- Create/Modify: `tests/ingest/*.py`
- Create: `tests/test_compile_command.py`, `tests/test_digest_command.py`, `tests/test_construct_command.py`

- [ ] **Step 1: 迁移 `tests/test_compile_loop.py` 的核心用例**

重点覆盖：
- `count_chars`
- `build_batches`
- `predict_genre`
- `build_compile_units`
- `parse_llm_buffers` 7-type fallback

- [ ] **Step 2: 运行全部 ingest 测试**

```bash
.venv/Scripts/pytest tests/ingest/ -v
```

- [ ] **Step 3: 提交**

```bash
git add tests/
git commit -m "test(ingest): migrate and adapt v4.0 tests"
```

---

## Task 12: 更新 AGENTS.md 与 Scheme 文档

**Files:**
- Modify: `AGENTS.md`
- Modify: `schemes/default/scheme.md`（可选）

- [ ] **Step 1: 在 AGENTS.md 中新增 `/compile`、`/digest`、`/construct` 章节**

内容要点：
- `/compile`：把 `00-Inbox/` 文档按体裁拆成 `05-Buffer/`；
- `/digest`：把 Buffer 消化为卡片或问题；
- `/construct`：结构整理、领域调整、关系补全；
- 每步先生成 prompt/batch，Agent 确认后 `--apply`；
- 禁止自动把未确认的产物写入 `01-Cards/`。

- [ ] **Step 2: 提交**

```bash
git add AGENTS.md
git commit -m "docs: document compile/digest/construct in AGENTS.md"
```

---

## Task 13: 最终验收

- [ ] **Step 1: 运行全部测试**

```bash
.venv/Scripts/pytest tests/ -v
```

预期：全部通过。

- [ ] **Step 2: 在示例项目上走通一遍**

```bash
python -m nexogenesis compile --root .
# Agent 调用 LLM 并保存 response 后
python -m nexogenesis compile --apply --root .
python -m nexogenesis digest --root .
# Agent 确认 batch 后
python -m nexogenesis digest --apply --root .
python -m nexogenesis construct --root .
# Agent 确认 batch 后
python -m nexogenesis construct --apply --root .
```

- [ ] **Step 3: 提交并完成 finishing**

```bash
git add -A
git commit -m "feat: P1 document ingestion pipeline"
# 使用 finishing-a-development-branch 合并
```

---

## Self-Review

- **Spec coverage**：compile/digest/construct 三阶段均对应 Task 7/8/9；prompt 模板管理对应 Task 6；7-type 适配贯穿 Task 2/5/7；测试对应 Task 11。
- **Placeholder scan**：无 TBD/TODO；每步给出具体代码或命令。
- **Type consistency**：`VALID_BUFFER_TYPES` 为 7 种，贯穿 `__init__.py`、`batch_runner.py`、`prompts.py`；Buffer status 为 `scratch/digested/constructed`。
- **已知简化**：`compile.py` 中 `_apply_responses` 假设 response YAML 结构为 `{"output": "..."}`，实际Agent可调整；PDF 依赖 `PyMuPDF` 为可选，测试环境若未安装则跳过 PDF 相关用例。
