---
name: nexo-digest
description: >-
  Runs Nexogenesis digest (skeleton nourishment + object creation): enrich
  existing cards and create new field objects from Buffer. Use when the user
  says 消化, /digest, 开始消化, or Buffer has scratch awaiting cards.
---

# nexo-digest（记忆体 · 消化）

## 触发条件

- 用户说「消化」「/digest」「开始消化」；
- `05-Buffer/` 中有 `status: scratch` 的文件。

## 步骤

1. `python -m nexogenesis digest --plan --root .`
   - 预览本波 Buffer 选择与深读卡。
2. `python -m nexogenesis digest --root .`
   - 生成本波 prompt 到 `.nexogenesis/tmp/digest/prompt.md`。
3. 必读：`01-Cards/_meta/body-structure.md` + `01-Cards/_meta/card-exemplars/`。
4. 按 prompt 写 `.nexogenesis/tmp/digest/batch.yaml`。
   - `operation.approved_by` 留 `"user"`，除非用户已授权 `--auto`。
5. 自检：YAML 格式、必需字段、`consumed_buffers`、无幽灵链接。
6. `python -m nexogenesis digest --apply --root .`
   - 或用户授权后 `digest --auto`。
7. 简短报告：enrich / 新建 / skip / conflict / Profile 更新 各几条。

## 主职

- 用本波 scratch Buffer **滋养已有骨架**（enrich 优先）；
- 遇到真正新、重要且可独立复用的质料时**果断新建 Card**；
- 从 Buffer 中提取领域级立场/价值取向/推理模式，追加到 `02-Profile/`；
- 结构调整、近义合并、升枢纽留给 `nexo-construct`。

## 必读文档

- `01-Cards/_meta/ontology.md`
- `01-Cards/_meta/body-structure.md`
- `01-Cards/_meta/card-exemplars/`
- `schemes/default/prompts/digest.txt`

## 不要

- 绕过 `write --batch` 直接改 `01-Cards/` 或 `02-Profile/`；
- 把 RAG/discussion 当成熟 Card 写入；
- 在消化阶段做大规模合并或目录重建。
