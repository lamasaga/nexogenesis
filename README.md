# Nexogenesis

面向思想者或学派的知识架构体系：用大模型**聚合涌现**可修订的知识骨架（而非把书自动切成碎片的批处理器），经讨论、反馈、分析与建构持续校准。

- **第一次了解项目** → [`docs/项目快速理解.md`](docs/项目快速理解.md)（推荐从这里读）
- **日常命令与 AI 规矩** → [`AGENTS.md`](AGENTS.md)（总原则 §一；CLI 速查 §5.0）
- **卡片正文结构** → `01-Cards/_meta/body-structure.md`

技术专题：`docs/2026-07-27-retrieval-graph-rag-design.md`（双轨检索）、`docs/2026-07-28-thinking-body-attention-design.md`（思维体记忆与注意力）。

## 快速开始

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m nexogenesis init
python -m nexogenesis validate
python -m nexogenesis doctor
python -m nexogenesis compile --plan   # 预览 Inbox 分波；默认每波少量文档
# compile 后先 --check-responses，再 --apply（可 --response 逐个落盘）
# digest --auto（Agent 自审 batch 后落盘）；construct --auto → --auto --lens …
# 完整 CLI 列表见 AGENTS.md §5.0
```
