---
name: nexo-digest
description: |
  Nexogenesis 消化：读取 05-Buffer/ 中 scratch Buffer，enrich 已有卡片，
  并在真正新、重要且可独立复用时新建领域对象。当用户说「消化」「/digest」
  「开始消化」或 05-Buffer/ 中有 scratch 文件时触发。
compatibility: Nexogenesis 项目，已初始化 .agent/reference/ 与 schemes/default/prompts/
---

# Grounding（按顺序必读）

1. `.agent/reference/constraint-layers.md` — 约束分层与写入权限。
2. `.agent/reference/card-contracts/body-structure.md` — 七型正文结构。
3. `.agent/reference/card-contracts/ontology.md` — 卡片类型与关系。
4. `.agent/reference/card-contracts/card-exemplars/` — 写法正例。
5. `.agent/reference/ingest-pipeline.md` §digest — 消化纪律。
6. `.agent/reference/write-transaction.md` — `write --batch` 规则。
7. `schemes/default/prompts/digest.txt` — 消化语义 prompt。

# Workflows

1. 预览本波 Buffer：
   ```bash
   python -m nexogenesis digest --plan --root .
   ```
2. 生成本波 prompt：
   ```bash
   python -m nexogenesis digest --root .
   ```
3. 读取 `.nexogenesis/tmp/digest/prompt.md` 与必选参考文档。
4. 按 prompt 写 `.nexogenesis/tmp/digest/batch.yaml`：
   - `operation.approved_by: user`（除非用户已授权 `--auto`）；
   - `operation.consumed_buffers` 列出实际消费的 Buffer 路径；
   - 空库必须先写至少一张 `domain` 卡。
5. 自检：YAML 格式、必填字段、无幽灵链接、类型必需槽存在。
6. 应用：
   ```bash
   python -m nexogenesis digest --apply --root .
   ```
   或用户授权后：
   ```bash
   python -m nexogenesis digest --auto --root .
   ```
7. 报告：enrich / 新建 / skip / conflict / Profile 更新 各几条。

# Invariants

- 必须先有 domain 骨架，再挂实例卡。
- 所有写入必须经 `write --batch`。
- `origin: system` 未经用户批准不得标 `mature` 或 `theory_status: active`。
- enrich 优先；真正新、重要且可独立复用才新建。
- 消化阶段只做 enrich 与新建，大规模合并/升枢纽留给 `nexo-construct`。
- 从 Buffer 中提取领域级立场/价值取向/推理模式时，追加到 `02-Profile/`。

# Anti-patterns

- 把 ingest 做成切书批处理器。
- 用「原文未提及」/标题回声凑格式。
- 在消化阶段绕过 `write --batch` 直接改卡。
- 把 RAG/discussion 命中直接写入 relations 或新建 Card。
- 为每片 Buffer 强制建一张卡。
