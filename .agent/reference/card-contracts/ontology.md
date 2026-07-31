---
scheme: "default"
version: "0.3.0"
updated: "2026-07-30"
---

# 当前元结构契约

本契约面向**社科领域思想结构化**：沉淀可支撑推理、分析与判断的领域知识体。

## 卡片类型（仅 Card）

| 类型 | 领域功能 | 典型对象 |
|---|---|---|
| `domain` | 领域骨架：划定思想领域、核心问题与边界 | 政治经济学、教育社会学、认知科学 |
| `claim` | 领域主张/原则/立场：可复述、可争辩的判断 | 「制度摩擦常被低估」「反馈应指出可操作差距」 |
| `phenomenon` | 可观察模式：重复出现的经验事实 | 古雅措辞炫耀性浪费、商品产能周期 |
| `model` | 解释结构：说明复杂事物的机制与组件 | 安全伙伴再分配、小院高墙获取性战略 |
| `method` | 分析路径：怎么做研究或怎么判断 | 观察炫耀性浪费迹象、比较历史分析 |
| `entity` | 关键对象：学派、制度、人物、组织 | 有闲阶级、投资银行家、制度学派 |
| `conflict` | 领域张力：两个及以上主张/模型/方法之间的对立 | 管理替代与时间购买之争 |

**`claim` 的扩展语义**：本系统用 `claim` 承载领域内的主张、原则与学派立场。当一张 claim 代表特定学派立场时，frontmatter 可用 `school` 标注学派来源，并在正文中说明与对立立场的核心分歧。

## Buffer 材料角色（仅 Buffer）

meaning-unit, detail, evidence, artifact-table, artifact-figure, tension, link-hypothesis, profile-seed

正文骨架与校验规则见 `body-structure.md`；写法正例见同目录 `card-exemplars/`。

## 关系类型

extends, supports, conflicts-with, involves, example-of, applies-to, based-on, influences

**重要区分**：
- `conflicts-with` 用于两张 `claim`/`model` 卡之间，表示它们直接矛盾；
- 在社科领域中，`claim` 与 `claim` 之间的 `conflicts-with` 常代表学派立场或理论传统的直接对立；
- `involves` 仅用于一张 `conflict` 卡指向它涉及的各方（claim/model/entity/method）。

## 结构涌现

- 聚类 → domain + domains
- 区分 → conflict + conflicts-with / involves
- 衔接 → relations（默认）+ model / method（升格）

## 领域索引生成规则

从所有卡片的 `domains` 字段反向生成。
