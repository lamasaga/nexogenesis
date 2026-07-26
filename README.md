# Nexogenesis

知识-思维涌现系统。运行契约见 `AGENTS.md`，正文结构见 `01-Cards/_meta/body-structure.md`，机制说明见 `docs/2026-07-26-buffer-card-structure-draft.md`，总览见 `docs/智构涌现介绍.md`。

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
```
