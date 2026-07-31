---
name: nexo-emerge
description: |
  Nexogenesis 捕获/涌现：从对话或 Buffer 中识别值得沉淀的思想，生成 ≤3 个候选，
  经用户确认后通过 write --batch 写入。当用户说「记一下」「/capture」「涌现」
  「这个值得记」时触发。
compatibility: Nexogenesis 项目，已初始化 .agent/reference/card-contracts/ 与 schemes/default/prompts/
---

# Grounding（按顺序必读）

1. `.agent/reference/constraint-layers.md` — 约束分层与写入权限。
2. `.agent/reference/card-contracts/body-structure.md` — 七型正文结构。
3. `.agent/reference/card-contracts/ontology.md` — 卡片类型与关系。
4. `.agent/reference/card-contracts/card-exemplars/` — 写法正例。
5. `.agent/reference/write-transaction.md` — `write --batch` 事务规则。
6. `schemes/default/prompts/digest.txt` — 当候选来自 Buffer 时参考消化语义。

# Workflows

> 完整 CLI 参数见 [`.agent/reference/harness-cli.md`](.agent/reference/harness-cli.md)；以下只列出本 skill 的典型调用顺序。

1. 判断来源：
   - 来自用户对话 → `origin: user`；
   - 来自文档/Buffer → `origin: document` 或 `external`；
   - 来自系统推断 → `origin: system`。
2. 生成 ≤3 个候选卡片或 Profile 字段：
   - 明确 `id`、`title`、`type`、`domains`、`maturity`、`lifecycle`；
   - 一句话主张/核心思想不可复读标题；
   - 依据须有机制或事实。
3. 向用户展示候选，等待确认。禁止 `approved_by: agent` 直接落盘。
4. 用户确认后，写 `.nexogenesis/tmp/emerge/batch.yaml`：
   - `operation.approved_by: user`；
   - `operation.source` 注明对话/文档来源；
   - 列出 `writes`。
5. 自检：YAML 格式、必需字段、无幽灵链接。
6. 执行：
   ```bash
   python -m nexogenesis write --batch .nexogenesis/tmp/emerge/batch.yaml --root .
   ```
7. 报告：写入几张卡、是否更新 Profile、是否有 conflict 待后续 construct 处理。

# Invariants

- 捕获永远用户确认；对话路径禁止自动写卡。
- 所有写入必须经 `write --batch`。
- `origin: system` 候选不得标 `mature` 或 `theory_status: active`。
- 新建卡片必须满足对应类型的必需语义槽。
- 若候选与已有 Card 近义，优先 enrich 而非新建。

# Anti-patterns

- 不确认就批量写卡。
- 把一句话碎片包装成多张卡。
- 把文档观点标为用户立场。
- 用「原文未提及」凑格式。
