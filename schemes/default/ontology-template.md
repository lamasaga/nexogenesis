---
scheme: "default"
version: "0.2.0"
updated: "2026-07-27"
---

# 当前元结构契约

## 卡片类型（仅 Card）

domain, claim, phenomenon, model, method, entity, conflict

## Buffer 材料角色（仅 Buffer）

meaning-unit, detail, evidence, artifact-table, artifact-figure, tension, link-hypothesis, profile-seed

正文骨架与校验规则见 `01-Cards/_meta/body-structure.md`（init 后由方案复制或维护）。

## 关系类型

extends, supports, conflicts-with, involves, example-of, applies-to, based-on, influences

## 结构涌现

- 聚类 → domain + domains
- 区分 → conflict + conflicts-with / involves
- 衔接 → relations（默认）+ model / method（升格）

## 领域索引生成规则

从所有卡片的 `domains` 字段反向生成。
