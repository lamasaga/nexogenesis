---
name: nexo-construct
description: |
  Nexogenesis 建构：通盘诊断卡片网络，发现冗余/分裂/张力，通过单镜头操作优化结构。
  当用户说「建构」「/construct」「结构校准」或 digest 后图结构需要清理时触发。
compatibility: Nexogenesis 项目，已初始化 .agent/reference/ 与 schemes/default/prompts/
---

# Grounding（按顺序必读）

1. `.agent/reference/constraint-layers.md` — 约束分层。
2. `.agent/reference/card-contracts/ontology.md` — 卡片类型与关系。
3. `.agent/reference/card-contracts/body-structure.md` — 正文结构。
4. `.agent/reference/ingest-pipeline.md` §construct — 建构纪律。
5. `.agent/reference/write-transaction.md` — `write --batch` 规则。
6. `schemes/default/prompts/construct.txt` — 建构语义 prompt。
7. `schemes/default/prompts/construct-diagnose.txt` — 诊断 prompt。

# Workflows

> 完整 CLI 参数见 [`.agent/reference/harness-cli.md`](.agent/reference/harness-cli.md)；以下只列出本 skill 的典型调用顺序。

1. 默认诊断：
   ```bash
   python -m nexogenesis construct --root .
   ```
   生成 `lenses-report.md`、`suggested-lenses.txt`、`structure-ops-draft.md`。
2. 与用户确认镜头（或用户已授权则按 suggested 逐镜处理）。
3. 单镜头执行，禁止 `all`：
   ```bash
   python -m nexogenesis construct --lens cluster --root .
   # 或 distinguish / articulate / cross_source
   ```
4. 写 `.nexogenesis/tmp/construct/batch.yaml`。
5. 自检后 apply：
   ```bash
   python -m nexogenesis construct --apply --root .
   ```
   或：
   ```bash
   python -m nexogenesis construct --auto --lens <name> --root .
   ```
6. 需要空边挂 domain 时：
   ```bash
   python -m nexogenesis construct --apply-seed-links --root .
   ```
   勿把挂靠边当完成态。
7. 报告：合并 / 升格枢纽 / 补 conflict / 补语义边 / Profile 更新 各几条。

# Invariants

- 主职：通盘考虑、合并、调整、升枢纽与张力。
- 原则上不新建 Card；确实缺少枢纽时须在 operation 中解释原因。
- 禁止物理删除卡片，只用 `lifecycle: superseded`/`archived`。
- 禁止读完全库 Buffer 重建目录。
- 涌现新的领域级理念/思维模型时，追加到 `02-Profile/`。

# Anti-patterns

- 把建构当第二次消化继续大量新建 Card。
- 不做诊断直接 apply。
- 一次使用多个 lens（`--lens all`）。
- 把 seed-links 当成完整关系网。
- 删除卡片而不是标记 superseded。
