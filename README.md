# Nexogenesis

**当前版本：`v0.15`**（git tag；下一里程碑约束分层锚点 `v0.16-pre-constraint-layers`）

　　查阅历史版本：`git tag -l "v0.*"`。近期锚点：`v0.14` 流水线重定向，`v0.15` 阅读窗，`v0.16-pre-constraint-layers` 起 AGENTS+Skills+环节约束。

面向社科领域的知识架构体系：用大模型把领域思想**结构化**为可支撑推理、分析与判断的知识体，同时沉淀可被思维体复用的领域级思考特质。

- **知识体**：`01-Cards/` + `05-Buffer/` 沉淀领域对象（主张、模型、现象、方法、实体、冲突、领域）。
- **思维体**：`nexo-talk` / `nexo-judge` / `nexo-emerge` 利用知识结构进行推理、分析与判断，不替代知识体写入。
- **领域 Profile**：`02-Profile/领域理念.md` 与 `02-Profile/领域思维模型.md` 记录领域级立场、价值取向、心智模型与推理模式，供思维体作为透镜复用。

系统强调**聚合涌现**，不是把书自动切成碎片的批处理器。

- **第一次了解项目** → [`docs/项目快速理解.md`](docs/项目快速理解.md)（推荐从这里读）
- **约束分层（宪法 / Skills / 环节）** → [`docs/2026-07-30-constraint-layers.md`](docs/2026-07-30-constraint-layers.md)
- **日常命令与 AI 规矩** → [`AGENTS.md`](AGENTS.md)（总原则 §一；CLI 速查 §5.0）
- **Agent 编排技能** → [`.agent/skills/`](.agent/skills/)（`nexo-talk` / `nexo-emerge` / `nexo-judge` / `nexo-compile` / `nexo-digest` / `nexo-construct`）
- **卡片正文结构** → `01-Cards/_meta/body-structure.md`
- **卡片写法正例** → [`01-Cards/_meta/card-exemplars/`](01-Cards/_meta/card-exemplars/)
- **样本工作区（历史）** → [`docs/卡片样本/`](docs/卡片样本/)

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
