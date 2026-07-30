---
name: nexo-construct
description: >-
  Runs Nexogenesis construct (structure calibration): diagnose, pick one lens,
  merge hubs tensions — not a second digest and not bulk card creation. Use when
  the user says 建构, /construct, 结构校准, or after digest when the graph needs
  cleanup.
---

# nexo-construct（记忆体 · 建构）

## 触发条件

- 用户说「建构」「/construct」「结构校准」；
- digest 之后图结构需要清理（冗余、分裂、orphan、张力未显化）。

## 步骤

1. `python -m nexogenesis construct --root .`
   - 默认 diagnose：生成 `lenses-report.md`、`suggested-lenses.txt`、`structure-ops-draft.md`。
2. 与用户确认镜头（或用户已说「开始建构」则按 suggested 逐镜处理）。
3. `python -m nexogenesis construct --lens <cluster|distinguish|articulate|cross_source> --root .`
   - 禁止 `all`；一次一镜。
4. 写 `.nexogenesis/tmp/construct/batch.yaml`。
5. 自检后 `--apply` 或 `--auto --lens <name>`。
6. 需要空边挂 domain 时用 `construct --apply-seed-links`
   - 勿把挂靠边当完成态。
7. 简短报告：合并 / 升格枢纽 / 补 conflict / 补语义边 / Profile 更新 各几条。

## 主职

- **通盘考虑**已有卡片网；
- 发现冗余/分裂 → 合并（superseded）或调整归属；
- 升 entity/model 枢纽；
- 显化张力：补 conflict + involves；
- 补语义边；
- 涌现新的领域级理念/思维模型时，追加到 `02-Profile/`。

## 纪律

- 原则上**不新建 Card**；digest 阶段已建立的对象由 construct 组织成结构。
- 只有在通盘考虑后确实缺少枢纽时才允许新建，并须在 operation 中解释原因。
- 禁止物理删除卡片，只用 `lifecycle: superseded`/`archived`。
- 禁止读完全库 Buffer 重建目录。

## 必读文档

- `01-Cards/_meta/ontology.md`
- `01-Cards/_meta/body-structure.md`
- `01-Cards/_meta/card-exemplars/`
- `schemes/default/prompts/construct.txt`
- `schemes/default/prompts/construct-diagnose.txt`
