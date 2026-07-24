# Nexogenesis P0 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 Nexogenesis 第一个里程碑：对话-捕获-回答闭环所需的最小 harness（统一 CLI + AGENTS.md + 默认 Scheme）。

**Architecture:** 用 Python 3.13 构建 `nexogenesis` 包，提供 `init/validate/index/write/doctor/migrate` 命令；所有写入走 `write --batch` 原子事务；markdown 为事实之源；生成索引视图辅助 AI 渐进阅读。

**Tech Stack:** Python 3.13, PyYAML, jsonschema, pytest, git hooks。

---

## 文件结构

```text
NexogenesisV0.1/
├── pyproject.toml
├── requirements.txt
├── .gitignore
├── AGENTS.md                         # 运行时手册
├── README.md                         # 项目说明
├── hooks/pre-commit                  # git pre-commit hook
├── nexogenesis/                      # Python 包
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                        # Click 命令入口
│   ├── models.py                     # 数据模型与枚举
│   ├── schemas.py                    # JSON Schema
│   ├── yaml_utils.py                 # 安全 YAML 读写 + 原子写
│   ├── store.py                      # 卡片加载、索引、孤儿/幽灵链接检查
│   ├── journal.py                    # Journal 追加
│   ├── operations.py                 # batch 解析与执行
│   └── commands/
│       ├── __init__.py
│       ├── init.py
│       ├── validate.py
│       ├── index.py
│       ├── write.py
│       ├── doctor.py
│       └── migrate.py
├── schemes/default/                  # 默认沉淀方案
│   ├── scheme.md
│   ├── ontology-template.md
│   ├── genre-strategies.md
│   ├── profile-template.md
│   └── migration.md
├── tests/                            # pytest 测试
│   ├── conftest.py
│   ├── test_yaml_utils.py
│   ├── test_store.py
│   ├── test_validate.py
│   ├── test_index.py
│   ├── test_journal.py
│   ├── test_write.py
│   └── fixtures/
│       └── ...
├── 00-Inbox/
├── 01-Cards/
│   └── _meta/
├── 02-Profile/
├── 03-Archive/
├── 04-OutBox/
├── 05-Buffer/                        # P1 启用，P0 只建目录
├── 06-Journal/
└── docs/
    └── 2026-07-24-nexogenesis-design.md
```

---

## Task 1: 项目脚手架与依赖

**Files:**
- Create: `NexogenesisV0.1/pyproject.toml`
- Create: `NexogenesisV0.1/requirements.txt`
- Create: `NexogenesisV0.1/.gitignore`
- Create: `NexogenesisV0.1/nexogenesis/__init__.py`
- Create: `NexogenesisV0.1/nexogenesis/__main__.py`
- Create: `NexogenesisV0.1/README.md`

- [ ] **Step 1: 创建 `pyproject.toml`**

```toml
[project]
name = "nexogenesis"
version = "0.1.0"
description = "Personal thought emergence harness"
requires-python = ">=3.13"
dependencies = [
    "pyyaml>=6.0",
    "jsonschema>=4.0",
    "click>=8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
]

[project.scripts]
nexogenesis = "nexogenesis.cli:main"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 2: 创建 `requirements.txt`**

```text
pyyaml>=6.0
jsonschema>=4.0
click>=8.0
pytest>=8.0
```

- [ ] **Step 3: 创建 `.gitignore`**

```text
__pycache__/
*.pyc
.venv/
.env
.pytest_cache/
.nexogenesis/tmp/
```

- [ ] **Step 4: 创建包入口**

`nexogenesis/__init__.py`:
```python
__version__ = "0.1.0"
```

`nexogenesis/__main__.py`:
```python
from nexogenesis.cli import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 5: 创建最小 `README.md`**

```markdown
# Nexogenesis

新一代知识-思维涌现系统。详见 `AGENTS.md` 与 `docs/2026-07-24-nexogenesis-design.md`。

## 快速开始

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python -m nexogenesis init
python -m nexogenesis validate
```
```

- [ ] **Step 6: 初始化虚拟环境并安装依赖**

Run:
```bash
cd "NexogenesisV0.1"
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
```

Expected: 依赖安装成功，无报错。

- [ ] **Step 7: Commit**

```bash
cd "NexogenesisV0.1"
git init 2>/dev/null || true
git add pyproject.toml requirements.txt .gitignore nexogenesis/__init__.py nexogenesis/__main__.py README.md
git commit -m "chore: scaffold Nexogenesis P0 project"
```

---

## Task 2: 数据模型与枚举

**Files:**
- Create: `NexogenesisV0.1/nexogenesis/models.py`
- Test: `NexogenesisV0.1/tests/test_models.py`

- [ ] **Step 1: 创建枚举与模型**

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class CardType(str, Enum):
    DOMAIN = "domain"
    CLAIM = "claim"
    PHENOMENON = "phenomenon"
    MODEL = "model"
    METHOD = "method"
    ENTITY = "entity"
    CONFLICT = "conflict"


class RelationType(str, Enum):
    EXTENDS = "extends"
    SUPPORTS = "supports"
    CONFLICTS_WITH = "conflicts-with"
    INVOLVES = "involves"
    EXAMPLE_OF = "example-of"
    APPLIES_TO = "applies-to"
    BASED_ON = "based-on"
    INFLUENCES = "influences"


class Origin(str, Enum):
    USER = "user"
    SYSTEM = "system"
    DOCUMENT = "document"
    EXTERNAL = "external"


class Maturity(str, Enum):
    SEED = "seed"
    GROWING = "growing"
    MATURE = "mature"


class Lifecycle(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class TheoryStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DORMANT = "dormant"


@dataclass
class Relation:
    target: str
    type: RelationType
    note: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Relation":
        return cls(
            target=data["target"],
            type=RelationType(data["type"]),
            note=data.get("note", ""),
        )


@dataclass
class Card:
    id: str
    title: str
    type: CardType
    maturity: Maturity
    lifecycle: Lifecycle
    domains: list[str]
    origin: Origin
    sources: list[str]
    relations: list[Relation]
    created: str
    updated: str
    body: str
    theory_status: TheoryStatus | None = None
    superseded_by: str | None = None
    path: str | None = None

    @classmethod
    def from_dict(cls, id: str, data: dict[str, Any], body: str, path: str | None = None) -> "Card":
        return cls(
            id=id,
            title=data["title"],
            type=CardType(data["type"]),
            maturity=Maturity(data["maturity"]),
            lifecycle=Lifecycle(data["lifecycle"]),
            domains=list(data.get("domains", [])),
            origin=Origin(data["origin"]),
            sources=list(data.get("sources", [])),
            relations=[Relation.from_dict(r) for r in data.get("relations", [])],
            created=data["created"],
            updated=data["updated"],
            body=body,
            theory_status=TheoryStatus(data["theory_status"]) if data.get("theory_status") else None,
            superseded_by=data.get("superseded_by"),
            path=path,
        )


@dataclass
class ProfileQuestion:
    question: str
    added_at: str
    status: str = "active"


@dataclass
class JournalEntry:
    operation_id: str
    timestamp: str
    action: str
    targets: list[str]
    source: str
    approved_by: str
```

- [ ] **Step 2: 写模型测试**

`tests/test_models.py`:
```python
from nexogenesis.models import Card, CardType, Maturity, Lifecycle, Origin, RelationType


def test_card_from_dict():
    data = {
        "title": "测试主张",
        "type": "claim",
        "maturity": "growing",
        "lifecycle": "active",
        "domains": ["teaching"],
        "origin": "user",
        "sources": ["2026-07-24 对话"],
        "relations": [{"target": "other", "type": "supports"}],
        "created": "2026-07-24",
        "updated": "2026-07-24",
    }
    card = Card.from_dict("test-claim", data, "正文")
    assert card.type == CardType.CLAIM
    assert card.maturity == Maturity.GROWING
    assert card.relations[0].type == RelationType.SUPPORTS
```

- [ ] **Step 3: 运行测试**

Run:
```bash
cd "NexogenesisV0.1"
.venv/Scripts/pytest tests/test_models.py -v
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
cd "NexogenesisV0.1"
git add nexogenesis/models.py tests/test_models.py
git commit -m "feat: add data models and enums"
```

---

## Task 3: 安全 YAML 读写与原子写入

**Files:**
- Create: `NexogenesisV0.1/nexogenesis/yaml_utils.py`
- Test: `NexogenesisV0.1/tests/test_yaml_utils.py`

- [ ] **Step 1: 实现工具函数**

```python
import os
import tempfile
from pathlib import Path

import yaml


def load_yaml(path: Path | str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def dump_yaml(data: dict, path: Path | str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def atomic_write_file(path: Path | str, content: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise


def split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = yaml.safe_load(parts[1]) or {}
    body = parts[2].lstrip("\n")
    return meta, body


def merge_frontmatter(meta: dict, body: str) -> str:
    yaml_text = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).rstrip()
    return f"---\n{yaml_text}\n---\n\n{body}"
```

- [ ] **Step 2: 写测试**

`tests/test_yaml_utils.py`:
```python
from pathlib import Path

from nexogenesis.yaml_utils import (
    atomic_write_file,
    dump_yaml,
    load_yaml,
    merge_frontmatter,
    split_frontmatter,
)


def test_round_trip_yaml(tmp_path: Path):
    path = tmp_path / "test.yaml"
    dump_yaml({"a": 1}, path)
    assert load_yaml(path) == {"a": 1}


def test_atomic_write(tmp_path: Path):
    path = tmp_path / "out.txt"
    atomic_write_file(path, "hello")
    assert path.read_text(encoding="utf-8") == "hello"


def test_split_merge_frontmatter():
    text = "---\ntitle: T\n---\n\nbody"
    meta, body = split_frontmatter(text)
    assert meta == {"title": "T"}
    assert body == "body"
    restored = merge_frontmatter(meta, body)
    assert "---" in restored
```

- [ ] **Step 3: 运行测试**

Run:
```bash
cd "NexogenesisV0.1"
.venv/Scripts/pytest tests/test_yaml_utils.py -v
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
cd "NexogenesisV0.1"
git add nexogenesis/yaml_utils.py tests/test_yaml_utils.py
git commit -m "feat: add safe yaml and atomic write utilities"
```

---

## Task 4: Store 层（加载、索引、孤儿/幽灵链接检查）

**Files:**
- Create: `NexogenesisV0.1/nexogenesis/store.py`
- Test: `NexogenesisV0.1/tests/test_store.py`
- Create fixture files under `NexogenesisV0.1/tests/fixtures/`

- [ ] **Step 1: 实现 store**

```python
from dataclasses import dataclass, field
from pathlib import Path

from nexogenesis.models import Card, CardType, RelationType
from nexogenesis.yaml_utils import split_frontmatter


@dataclass
class Store:
    cards_dir: Path
    cards: dict[str, Card] = field(default_factory=dict)
    by_domain: dict[str, list[str]] = field(default_factory=dict)
    conflicts_involving: dict[str, list[str]] = field(default_factory=dict)
    theories: list[str] = field(default_factory=list)

    def load(self) -> "Store":
        self.cards = {}
        self.by_domain = {}
        self.conflicts_involving = {}
        self.theories = []
        for path in sorted(self.cards_dir.glob("*.md")):
            if path.name.startswith("_"):
                continue
            text = path.read_text(encoding="utf-8")
            meta, body = split_frontmatter(text)
            if not meta or "id" not in meta:
                continue
            card = Card.from_dict(meta["id"], meta, body, str(path))
            self.cards[card.id] = card
            for d in card.domains:
                self.by_domain.setdefault(d, []).append(card.id)
            if card.theory_status:
                self.theories.append(card.id)
        self._build_conflict_index()
        return self

    def _build_conflict_index(self) -> None:
        self.conflicts_involving = {}
        for card in self.cards.values():
            if card.type != CardType.CONFLICT:
                continue
            for rel in card.relations:
                if rel.type == RelationType.INVOLVES:
                    self.conflicts_involving.setdefault(rel.target, []).append(card.id)

    def validate(self) -> tuple[list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []
        for card in self.cards.values():
            if not card.domains:
                errors.append(f"{card.id}: domains 为空")
            for d in card.domains:
                if d not in self.by_domain:
                    pass  # domain card 可能还没加载？已在 cards 中检查
                domain_card = self.cards.get(d)
                if domain_card is None:
                    errors.append(f"{card.id}: 领域 {d} 不存在")
                elif domain_card.type != CardType.DOMAIN:
                    errors.append(f"{card.id}: {d} 不是 domain 卡片")
            for rel in card.relations:
                if rel.target not in self.cards:
                    errors.append(f"{card.id}: 关系指向不存在的卡片 {rel.target}")
                if rel.type == RelationType.INVOLVES and card.type != CardType.CONFLICT:
                    errors.append(f"{card.id}: involves 只能用于 conflict 卡片")
            if card.lifecycle == "superseded" and not card.superseded_by:
                errors.append(f"{card.id}: lifecycle=superseded 时必须提供 superseded_by")
            if card.theory_status and card.type not in ("claim", "model"):
                errors.append(f"{card.id}: theory_status 只能用于 claim/model")
            if len(card.sources) > 12:
                warnings.append(f"{card.id}: sources 数量 {len(card.sources)} 超过建议值 12")
            if len(card.relations) > 12:
                warnings.append(f"{card.id}: relations 数量 {len(card.relations)} 超过建议值 12")
        return errors, warnings
```

- [ ] **Step 2: 创建 fixture**

`tests/fixtures/teaching.md`:
```markdown
---
id: "teaching"
title: "教学领域"
type: "domain"
maturity: "mature"
lifecycle: "active"
domains: ["teaching"]
origin: "user"
sources: ["2026-07-24 对话"]
relations: []
created: "2026-07-24"
updated: "2026-07-24"
---

教学领域的核心问题。
```

`tests/fixtures/feedback-gap-actionable.md`:
```markdown
---
id: "feedback-gap-actionable"
title: "教学反馈应优先指出可操作差距"
type: "claim"
maturity: "growing"
lifecycle: "active"
domains: ["teaching"]
origin: "user"
sources: ["2026-07-24 对话"]
relations:
  - target: "teaching"
    type: "applies-to"
created: "2026-07-24"
updated: "2026-07-24"
---

正文。
```

- [ ] **Step 3: 写测试**

`tests/test_store.py`:
```python
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
    assert fixture_store.by_domain["teaching"] == ["feedback-gap-actionable", "teaching"]


def test_validate_ok(fixture_store: Store):
    errors, warnings = fixture_store.validate()
    assert errors == []
```

- [ ] **Step 4: 运行测试**

Run:
```bash
cd "NexogenesisV0.1"
.venv/Scripts/pytest tests/test_store.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd "NexogenesisV0.1"
git add nexogenesis/store.py tests/test_store.py tests/fixtures/
git commit -m "feat: add store loading and validation"
```

---

## Task 5: JSON Schema

**Files:**
- Create: `NexogenesisV0.1/nexogenesis/schemas.py`
- Test: `NexogenesisV0.1/tests/test_schemas.py`

- [ ] **Step 1: 定义卡片 schema**

```python
CARD_SCHEMA = {
    "type": "object",
    "required": ["id", "title", "type", "maturity", "lifecycle", "domains", "origin", "sources", "relations", "created", "updated"],
    "properties": {
        "id": {"type": "string", "pattern": "^[a-z0-9-]+$"},
        "title": {"type": "string"},
        "type": {"enum": ["domain", "claim", "phenomenon", "model", "method", "entity", "conflict"]},
        "maturity": {"enum": ["seed", "growing", "mature"]},
        "lifecycle": {"enum": ["active", "superseded", "archived"]},
        "domains": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        "origin": {"enum": ["user", "system", "document", "external"]},
        "sources": {"type": "array", "items": {"type": "string"}},
        "relations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["target", "type"],
                "properties": {
                    "target": {"type": "string"},
                    "type": {"enum": ["extends", "supports", "conflicts-with", "involves", "example-of", "applies-to", "based-on", "influences"]},
                    "note": {"type": "string"},
                },
            },
        },
        "created": {"type": "string"},
        "updated": {"type": "string"},
        "theory_status": {"enum": ["draft", "active", "dormant"]},
        "superseded_by": {"type": "string"},
    },
}
```

- [ ] **Step 2: 提供校验函数**

```python
from jsonschema import validate, ValidationError


def validate_card_schema(data: dict) -> list[str]:
    try:
        validate(instance=data, schema=CARD_SCHEMA)
        return []
    except ValidationError as e:
        return [f"schema error: {e.message} at {list(e.path)}"]
```

- [ ] **Step 3: 写测试**

```python
from nexogenesis.schemas import validate_card_schema


def test_valid_card():
    data = {
        "id": "test",
        "title": "T",
        "type": "claim",
        "maturity": "growing",
        "lifecycle": "active",
        "domains": ["teaching"],
        "origin": "user",
        "sources": ["s"],
        "relations": [],
        "created": "2026-07-24",
        "updated": "2026-07-24",
    }
    assert validate_card_schema(data) == []


def test_invalid_type():
    data = {"type": "note"}  # missing many fields
    errors = validate_card_schema(data)
    assert any("note" in e for e in errors)
```

- [ ] **Step 4: 运行测试并 Commit**

```bash
cd "NexogenesisV0.1"
.venv/Scripts/pytest tests/test_schemas.py -v
git add nexogenesis/schemas.py tests/test_schemas.py
git commit -m "feat: add JSON schema validation for cards"
```

---

## Task 6: CLI 入口框架

**Files:**
- Create: `NexogenesisV0.1/nexogenesis/cli.py`
- Modify: `NexogenesisV0.1/nexogenesis/__main__.py` (no change needed)

- [ ] **Step 1: 创建 Click CLI**

```python
import click

from nexogenesis.commands.init import init_cmd
from nexogenesis.commands.validate import validate_cmd
from nexogenesis.commands.index import index_cmd
from nexogenesis.commands.write import write_cmd
from nexogenesis.commands.doctor import doctor_cmd
from nexogenesis.commands.migrate import migrate_cmd


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Nexogenesis harness CLI."""
    pass


main.add_command(init_cmd, name="init")
main.add_command(validate_cmd, name="validate")
main.add_command(index_cmd, name="index")
main.add_command(write_cmd, name="write")
main.add_command(doctor_cmd, name="doctor")
main.add_command(migrate_cmd, name="migrate")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 创建 commands 包**

`nexogenesis/commands/__init__.py`: empty

- [ ] **Step 3: 验证 CLI 可运行**

Run:
```bash
cd "NexogenesisV0.1"
.venv/Scripts/python -m nexogenesis --help
```

Expected: 显示命令列表。

- [ ] **Step 4: Commit**

```bash
cd "NexogenesisV0.1"
git add nexogenesis/cli.py nexogenesis/commands/__init__.py
git commit -m "feat: add Click CLI skeleton"
```

---

## Task 7: `init` 命令

**Files:**
- Create: `NexogenesisV0.1/nexogenesis/commands/init.py`
- Create: `NexogenesisV0.1/hooks/pre-commit`
- Create: `NexogenesisV0.1/schemes/default/ontology-template.md`
- Create: `NexogenesisV0.1/schemes/default/scheme.md`
- Create: `NexogenesisV0.1/schemes/default/profile-template.md`
- Test: `NexogenesisV0.1/tests/test_init.py`

- [ ] **Step 1: 实现 init 命令**

```python
import shutil
from pathlib import Path

import click


@click.command()
@click.option("--root", default=".", help="项目根目录")
def init_cmd(root: str):
    root_path = Path(root).resolve()
    dirs = [
        "00-Inbox",
        "01-Cards/_meta",
        "02-Profile",
        "03-Archive",
        "04-OutBox",
        "05-Buffer/claim",
        "05-Buffer/model",
        "05-Buffer/method",
        "05-Buffer/conflict",
        "05-Buffer/note",
        "06-Journal",
        "schemes/default",
        "tests/fixtures",
        ".nexogenesis/tmp",
    ]
    for d in dirs:
        (root_path / d).mkdir(parents=True, exist_ok=True)

    # copy default scheme files if not exist
    scheme_src = Path(__file__).parent.parent.parent / "schemes" / "default"
    scheme_dst = root_path / "schemes" / "default"
    for fname in ["scheme.md", "ontology-template.md", "profile-template.md"]:
        src = scheme_src / fname
        dst = scheme_dst / fname
        if src.exists() and not dst.exists():
            shutil.copy(src, dst)

    # install git hook if .git exists
    git_dir = root_path / ".git"
    if git_dir.exists():
        hook_src = root_path / "hooks" / "pre-commit"
        hook_dst = git_dir / "hooks" / "pre-commit"
        if hook_src.exists():
            shutil.copy(hook_src, hook_dst)
            hook_dst.chmod(0o755)
            click.echo("Installed git pre-commit hook.")

    ontology = root_path / "01-Cards" / "_meta" / "ontology.md"
    if not ontology.exists():
        template = scheme_dst / "ontology-template.md"
        if template.exists():
            shutil.copy(template, ontology)

    click.echo(f"Initialized Nexogenesis project at {root_path}")
```

- [ ] **Step 2: 创建默认 scheme 文件**

`schemes/default/scheme.md`:
```markdown
---
scheme_id: "default"
version: "0.1.0"
name: "默认沉淀方案"
based_on: "思维涌现mainV4"
---

# 默认沉淀方案

适用于个人思想沉淀与一般性知识管理。卡片类型 7 种，关系 8 种。
```

`schemes/default/ontology-template.md`:
```markdown
---
scheme: "default"
version: "0.1.0"
updated: "2026-07-24"
---

# 当前元结构契约

## 卡片类型

domain, claim, phenomenon, model, method, entity, conflict

## 关系类型

extends, supports, conflicts-with, involves, example-of, applies-to, based-on, influences

## 领域索引生成规则

从所有卡片的 `domains` 字段反向生成。
```

`schemes/default/profile-template.md`:
```markdown
# 问题清单

| 问题 | 提出时间 | 状态 | 关联卡片 |
|---|---|---|---|

# 待观察模式

（空）
```

- [ ] **Step 3: 创建 pre-commit hook**

`hooks/pre-commit`:
```bash
#!/bin/sh
python -m nexogenesis validate
```

- [ ] **Step 4: 写测试**

`tests/test_init.py`:
```python
from pathlib import Path

from click.testing import CliRunner

from nexogenesis.commands.init import init_cmd


def test_init_creates_directories(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(init_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "01-Cards" / "_meta" / "ontology.md").exists()
    assert (tmp_path / "06-Journal").exists()
```

- [ ] **Step 5: 运行测试并 Commit**

```bash
cd "NexogenesisV0.1"
.venv/Scripts/pytest tests/test_init.py -v
git add nexogenesis/commands/init.py schemes/default/ hooks/pre-commit tests/test_init.py
git commit -m "feat: add init command and default scheme"
```

---

## Task 8: `validate` 命令

**Files:**
- Create: `NexogenesisV0.1/nexogenesis/commands/validate.py`
- Test: `NexogenesisV0.1/tests/test_validate_command.py`

- [ ] **Step 1: 实现 validate**

```python
from pathlib import Path

import click

from nexogenesis.schemas import validate_card_schema
from nexogenesis.store import Store
from nexogenesis.yaml_utils import split_frontmatter


def run_validate(root_path: Path) -> tuple[list[str], list[str]]:
    cards_dir = root_path / "01-Cards"
    store = Store(cards_dir).load()
    schema_errors: list[str] = []
    for card in store.cards.values():
        meta, _ = split_frontmatter(Path(card.path).read_text(encoding="utf-8"))
        errs = validate_card_schema(meta)
        for e in errs:
            schema_errors.append(f"{card.id}: {e}")
    semantic_errors, warnings = store.validate()
    return schema_errors + semantic_errors, warnings


@click.command()
@click.option("--root", default=".", help="项目根目录")
@click.option("--strict", is_flag=True, help="warning 也视为错误")
def validate_cmd(root: str, strict: bool):
    root_path = Path(root).resolve()
    all_errors, warnings = run_validate(root_path)

    for e in all_errors:
        click.echo(f"ERROR: {e}")
    for w in warnings:
        click.echo(f"WARNING: {w}")

    if all_errors or (strict and warnings):
        raise click.ClickException("Validation failed.")
    click.echo("Validation passed.")
```

- [ ] **Step 2: 写测试**

`tests/test_validate_command.py`:
```python
from pathlib import Path

from click.testing import CliRunner

from nexogenesis.commands.init import init_cmd
from nexogenesis.commands.validate import validate_cmd


def test_validate_passes_after_init(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    result = runner.invoke(validate_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0
```

- [ ] **Step 3: 运行测试并 Commit**

```bash
cd "NexogenesisV0.1"
.venv/Scripts/pytest tests/test_validate_command.py -v
git add nexogenesis/commands/validate.py tests/test_validate_command.py
git commit -m "feat: add validate command"
```

---

## Task 9: `index` 命令

**Files:**
- Create: `NexogenesisV0.1/nexogenesis/commands/index.py`
- Test: `NexogenesisV0.1/tests/test_index_command.py`

- [ ] **Step 1: 实现 index**

```python
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
```

- [ ] **Step 2: 写测试**

`tests/test_index_command.py`:
```python
from pathlib import Path

from click.testing import CliRunner

from nexogenesis.commands.index import index_cmd
from nexogenesis.commands.init import init_cmd


def test_index_generates_files(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    result = runner.invoke(index_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "01-Cards" / "_meta" / "domain-index.md").exists()
```

- [ ] **Step 3: 运行测试并 Commit**

```bash
cd "NexogenesisV0.1"
.venv/Scripts/pytest tests/test_index_command.py -v
git add nexogenesis/commands/index.py tests/test_index_command.py
git commit -m "feat: add index command"
```

---

## Task 10: `journal` 模块与 `write --batch`

**Files:**
- Create: `NexogenesisV0.1/nexogenesis/journal.py`
- Create: `NexogenesisV0.1/nexogenesis/operations.py`
- Create: `NexogenesisV0.1/nexogenesis/commands/write.py`
- Test: `NexogenesisV0.1/tests/test_write_command.py`

- [ ] **Step 1: 实现 journal**

```python
from datetime import datetime, timezone
from pathlib import Path

from nexogenesis.yaml_utils import load_yaml, atomic_write_file, merge_frontmatter, split_frontmatter


def append(root: Path, operation_id: str, action: str, targets: list[str], source: str, approved_by: str) -> None:
    journal_dir = root / "06-Journal"
    journal_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    path = journal_dir / f"{month_key}.md"

    entry = f"- {now} | {operation_id} | {action} | targets={','.join(targets)} | source={source} | approved_by={approved_by}\n"
    if path.exists():
        text = path.read_text(encoding="utf-8")
        meta, body = split_frontmatter(text)
        body = body + entry
    else:
        meta = {"title": f"Journal {month_key}", "type": "journal"}
        body = entry
    atomic_write_file(path, merge_frontmatter(meta, body))
```

- [ ] **Step 2: 实现 operations**

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nexogenesis.models import CardType, Maturity, Lifecycle, Origin, TheoryStatus
from nexogenesis.yaml_utils import merge_frontmatter


@dataclass
class BatchOperation:
    operation_id: str
    source: str
    approved_by: str
    writes: list[dict[str, Any]]

    @classmethod
    def from_file(cls, path: Path) -> "BatchOperation":
        import yaml
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        op = data.get("operation", {})
        return cls(
            operation_id=op["id"],
            source=op["source"],
            approved_by=op["approved_by"],
            writes=data.get("writes", []),
        )


def card_meta_from_write(item: dict[str, Any]) -> dict[str, Any]:
    meta = {
        "id": item["id"],
        "title": item["title"],
        "type": item["type"],
        "maturity": item["maturity"],
        "lifecycle": item["lifecycle"],
        "domains": item["domains"],
        "origin": item["origin"],
        "sources": item.get("sources", []),
        "relations": item.get("relations", []),
        "created": item["created"],
        "updated": item["updated"],
    }
    if item.get("theory_status"):
        meta["theory_status"] = item["theory_status"]
    if item.get("superseded_by"):
        meta["superseded_by"] = item["superseded_by"]
    return meta
```

- [ ] **Step 3: 实现 write 命令（原子事务）**

`nexogenesis/commands/write.py`:

```python
import os
import tempfile
from pathlib import Path

import click

from nexogenesis import journal
from nexogenesis.commands.index import generate_indexes
from nexogenesis.commands.validate import run_validate
from nexogenesis.operations import BatchOperation, card_meta_from_write
from nexogenesis.yaml_utils import atomic_write_file, merge_frontmatter


def _append_profile_question(profile_path: Path, item: dict) -> None:
    lines = []
    if profile_path.exists():
        lines = profile_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = ["# 问题清单", "", "| 问题 | 提出时间 | 状态 |", "|---|---|---|"]
    lines.append(f"| {item['question']} | {item.get('added_at', '')} | active |")
    atomic_write_file(profile_path, "\n".join(lines) + "\n")


@click.command()
@click.option("--batch", required=True, type=click.Path(exists=True), help="batch YAML 文件")
@click.option("--root", default=".", help="项目根目录")
def write_cmd(batch: str, root: str):
    root_path = Path(root).resolve()
    cards_dir = root_path / "01-Cards"
    profile_path = root_path / "02-Profile" / "问题清单.md"
    batch_op = BatchOperation.from_file(Path(batch))

    card_writes = [w for w in batch_op.writes if w.get("target", "card") == "card"]
    profile_writes = [w for w in batch_op.writes if w.get("target") == "profile_question"]

    backup_files: list[tuple[Path, Path | None]] = []
    try:
        for item in card_writes:
            final_path = cards_dir / f"{item['id']}.md"
            meta = card_meta_from_write(item)
            content = merge_frontmatter(meta, item.get("body", ""))
            tmp = Path(tempfile.mktemp(dir=cards_dir, prefix=".tmp-", suffix=".md"))
            tmp.write_text(content, encoding="utf-8")
            backup = None
            if final_path.exists():
                backup = Path(tempfile.mktemp(dir=cards_dir, prefix=".bak-", suffix=".md"))
                backup.write_text(final_path.read_text(encoding="utf-8"), encoding="utf-8")
            os.replace(tmp, final_path)
            backup_files.append((final_path, backup))

        for pw in profile_writes:
            _append_profile_question(profile_path, pw)

        errors, warnings = run_validate(root_path)
        if errors:
            raise RuntimeError("; ".join(errors))

        journal.append(
            root_path,
            batch_op.operation_id,
            "write",
            [w["id"] for w in card_writes],
            batch_op.source,
            batch_op.approved_by,
        )
        generate_indexes(root_path)

    except Exception:
        for final_path, backup in backup_files:
            if backup and backup.exists():
                os.replace(backup, final_path)
            elif backup is None and final_path.exists():
                os.unlink(final_path)
        raise click.ClickException("Write failed and was rolled back.")
    finally:
        for _, backup in backup_files:
            if backup and backup.exists():
                os.unlink(backup)

    click.echo(f"Wrote {len(card_writes)} card(s), {len(profile_writes)} question(s).")
```

说明：
- `run_validate(root_path)` 和 `generate_indexes(root_path)` 分别是 `validate.py` 和 `index.py` 暴露的函数，避免在事务中启动子进程。

- [ ] **Step 5: 写测试**

`tests/test_write_command.py`:
```python
from pathlib import Path

from click.testing import CliRunner
import yaml

from nexogenesis.commands.init import init_cmd
from nexogenesis.commands.write import write_cmd


def test_write_creates_card(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])
    batch = tmp_path / "batch.yaml"
    batch.write_text(yaml.safe_dump({
        "operation": {"id": "op-1", "source": "对话", "approved_by": "user"},
        "writes": [{
            "target": "card",
            "id": "test-claim",
            "title": "测试主张",
            "type": "claim",
            "maturity": "growing",
            "lifecycle": "active",
            "domains": ["teaching"],
            "origin": "user",
            "sources": ["对话"],
            "relations": [],
            "created": "2026-07-24",
            "updated": "2026-07-24",
            "body": "正文",
        }]
    }), encoding="utf-8")
    result = runner.invoke(write_cmd, ["--batch", str(batch), "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "01-Cards" / "test-claim.md").exists()
    assert (tmp_path / "01-Cards" / "_meta" / "domain-index.md").exists()
```

- [ ] **Step 6: 运行测试并 Commit**

```bash
cd "NexogenesisV0.1"
.venv/Scripts/pytest tests/test_write_command.py -v
git add nexogenesis/journal.py nexogenesis/operations.py nexogenesis/commands/write.py tests/test_write_command.py
git commit -m "feat: add atomic write transaction"
```

---

## Task 11: `doctor` 命令

**Files:**
- Create: `NexogenesisV0.1/nexogenesis/commands/doctor.py`
- Test: `NexogenesisV0.1/tests/test_doctor_command.py`

- [ ] **Step 1: 实现 doctor**

```python
from pathlib import Path

import click

from nexogenesis.store import Store


@click.command()
@click.option("--root", default=".", help="项目根目录")
def doctor_cmd(root: str):
    root_path = Path(root).resolve()
    issues = []
    for d in ["01-Cards", "02-Profile", "06-Journal"]:
        if not (root_path / d).exists():
            issues.append(f"缺少目录: {d}")
    store = Store(root_path / "01-Cards").load()
    errors, warnings = store.validate()
    for e in errors:
        issues.append(e)
    for w in warnings:
        click.echo(f"WARNING: {w}")
    if issues:
        for i in issues:
            click.echo(f"ISSUE: {i}")
        raise click.ClickException("Doctor found issues.")
    click.echo("Doctor: OK")
```

- [ ] **Step 2: 运行测试并 Commit**

```bash
cd "NexogenesisV0.1"
.venv/Scripts/pytest tests/test_doctor_command.py -v
git add nexogenesis/commands/doctor.py tests/test_doctor_command.py
git commit -m "feat: add doctor command"
```

---

## Task 12: `migrate --dry-run` 命令

**Files:**
- Create: `NexogenesisV0.1/nexogenesis/commands/migrate.py`
- Create: `NexogenesisV0.1/schemes/default/migration.md`
- Test: `NexogenesisV0.1/tests/test_migrate_command.py`

- [ ] **Step 1: 实现 migrate dry-run**

```python
from pathlib import Path

import click

from nexogenesis.store import Store


@click.command()
@click.option("--to", required=True, help="目标 scheme_id")
@click.option("--root", default=".", help="项目根目录")
@click.option("--dry-run", is_flag=True, default=True, help="只生成报告，不执行")
def migrate_cmd(to: str, root: str, dry_run: bool):
    root_path = Path(root).resolve()
    store = Store(root_path / "01-Cards").load()
    click.echo(f"Migration dry-run to {to}")
    click.echo(f"Cards scanned: {len(store.cards)}")
    click.echo("No changes made (dry-run).")
```

- [ ] **Step 2: 创建 migration.md**

`schemes/default/migration.md`:
```markdown
# 默认方案迁移规则

## 从旧类型映射

- notion/principle → claim
- group → entity
- note → 保留在 Buffer
```

- [ ] **Step 3: Commit**

```bash
cd "NexogenesisV0.1"
git add nexogenesis/commands/migrate.py schemes/default/migration.md tests/test_migrate_command.py
git commit -m "feat: add migrate dry-run command"
```

---

## Task 13: 新版 `AGENTS.md`

**Files:**
- Create/Overwrite: `NexogenesisV0.1/AGENTS.md`

- [ ] **Step 1: 根据 spec 撰写 AGENTS.md**

内容需包含：

- 核心原则（底座主权、写入统一入口、复杂度证据）；
- 目录结构；
- 卡片类型 7 种、关系 8 种、frontmatter 字段；
- 指令集：`/talk` `/capture` `/answer` `/judge` `/theorize` `/reflect`；
- `/capture` 候选为 claim/question/conflict；
- 所有写入经 `python -m nexogenesis write --batch`；
- 验证、索引、Journal 命令；
- 安全边界：origin:system 不自动 mature、不删除卡片只标记 lifecycle；
- 第一个里程碑验收标准。

- [ ] **Step 2: Commit**

```bash
cd "NexogenesisV0.1"
git add AGENTS.md
git commit -m "docs: write AGENTS.md for P0"
```

---

## Task 14: 集成测试与验收

**Files:**
- Create: `NexogenesisV0.1/tests/test_acceptance.py`

- [ ] **Step 1: 编写验收测试**

```python
from pathlib import Path

from click.testing import CliRunner
import yaml

from nexogenesis.commands.init import init_cmd
from nexogenesis.commands.validate import validate_cmd
from nexogenesis.commands.index import index_cmd
from nexogenesis.commands.write import write_cmd


def test_closed_capture_loop(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(init_cmd, ["--root", str(tmp_path)])

    # 模拟用户批准一个 claim 和一个 question
    batch = tmp_path / "batch.yaml"
    batch.write_text(yaml.safe_dump({
        "operation": {"id": "conv-20260724-001", "source": "对话 2026-07-24", "approved_by": "user"},
        "writes": [
            {
                "target": "card",
                "id": "feedback-gap-actionable",
                "title": "教学反馈应优先指出可操作差距",
                "type": "claim",
                "maturity": "growing",
                "lifecycle": "active",
                "domains": ["teaching"],
                "origin": "user",
                "sources": ["2026-07-24 对话"],
                "relations": [],
                "created": "2026-07-24",
                "updated": "2026-07-24",
                "body": "正文内容",
            },
            {
                "target": "profile_question",
                "question": "怎样区分有效反思与自我感动？",
                "added_at": "2026-07-24",
            },
        ]
    }), encoding="utf-8")

    result = runner.invoke(write_cmd, ["--batch", str(batch), "--root", str(tmp_path)])
    assert result.exit_code == 0

    # 校验通过
    result = runner.invoke(validate_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0

    # 索引存在
    result = runner.invoke(index_cmd, ["--root", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "01-Cards" / "_meta" / "domain-index.md").exists()

    # 重复写入同一 batch 不会创建重复卡片（id 相同则更新）
    result = runner.invoke(write_cmd, ["--batch", str(batch), "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert len(list((tmp_path / "01-Cards").glob("*.md"))) == 2  # ontology + claim
```

- [ ] **Step 2: 运行全部测试**

Run:
```bash
cd "NexogenesisV0.1"
.venv/Scripts/pytest tests/ -v
```

Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
cd "NexogenesisV0.1"
git add tests/test_acceptance.py
git commit -m "test: add P0 acceptance test"
```

---

## Task 15: 最终验收与文档

- [ ] **Step 1: 安装 pre-commit hook 并验证**

Run:
```bash
cd "NexogenesisV0.1"
python -m nexogenesis init
# 如果有 .git 目录，确认 hook 已安装
ls -la .git/hooks/pre-commit
```

- [ ] **Step 2: 运行端到端演示**

手动演示：
1. 在 `01-Cards/_meta/` 创建 `teaching.md` domain 卡；
2. 创建 batch 并运行 `python -m nexogenesis write --batch batch.yaml`；
3. 运行 `python -m nexogenesis validate`；
4. 运行 `python -m nexogenesis index`；
5. 检查 `01-Cards/_meta/domain-index.md`。

- [ ] **Step 3: 更新 README（可选）**

如果 AGENTS.md 已足够，README 可保持最小。

- [ ] **Step 4: 最终 Commit**

```bash
cd "NexogenesisV0.1"
git add -A
git commit -m "feat: complete Nexogenesis P0 harness"
```

---

## Self-Review Checklist

- [x] Spec coverage：每个 spec 章节都有对应任务。
- [x] Placeholder scan：计划中没有 TBD/TODO。
- [x] Type consistency：模型、schema、store 使用相同的字段名和枚举。
- [x] 注意：`validate` 和 `index` 命令已暴露 `run_validate` / `generate_indexes` 函数，供 `write` 事务直接调用，避免子进程开销。
