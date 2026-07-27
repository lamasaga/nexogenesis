---
version: "0.2.2"
updated: "2026-07-27"
---

# 正文结构契约（body-structure）

　　compile / digest / validate 共同引用的活契约。修改须经用户确认。机制说明见 `docs/2026-07-26-buffer-card-structure-draft.md`。

## 1. 两层分工

- **Buffer（质料层）**：按意义单元整理原材料；用 `role` 标注用途；不定 Card `type`；不写 `id` / `relations`。
- **Card（本体对象层）**：承诺维护的知识对象；`type` 七型；有 id / domains / relations / lifecycle。

结构涌现：

| 机制 | 落点 |
|---|---|
| 聚类 | `domain` Card + `domains` |
| 区分 | `conflict` Card + `conflicts-with` / `involves` |
| 衔接 | `relations`（默认）+ `model` / `method`（升格） |

## 2. Buffer

### 2.1 frontmatter

必需：`title`、`role`、`created`、`updated`、`source`、`status`  
建议：`genre`、`perspective`  
可选：`proposed_card_type`、`proposed_domains`、`related_within_batch`

禁止：`type`（七型）、`id`、`relations`；正文禁止 `[[ ]]`。

### 2.2 role 枚举

`meaning-unit` | `detail` | `evidence` | `artifact-table` | `artifact-figure` | `tension` | `link-hypothesis` | `profile-seed`

目录：`05-Buffer/<role>/`

### 2.3 命名

文件名：`YYYY-MM-DD-HHMMSS-<序号>-<中文标题>.md`  
允许：汉字、字母、数字、连字符 `-`；禁止路径危险字符与空白。

### 2.4 意义单元必需槽（`meaning-unit`）

| 语义槽 | 推荐标题 | 可接受同义 |
|---|---|---|
| 核心表达 | 核心表达 | 一句话主张, 核心思想, 核心问题, 定义, 模式描述 |
| 依据与细节 | 依据与细节 | 依据, 细节, 关键组件, 步骤, 关键属性 |
| 限制与边界 | 限制与边界 | 已知限制, 失效边界, 适用边界, 边界, 反例与失效条件, 调和可能, 边界与局限 |
| 原文摘录 | 原文摘录 | 摘录, 原文 |

缺槽写法：正文中写 `原文未提及：……`。

质料丰富性（compile 宜略厚）：

- 「依据与细节」尽量保留公式、符号、数据集/指标名、关键数值与对照条件，避免空泛转述。
- 「原文摘录」建议 **2–3** 条短摘录（`>` 引用），优先可核对主张的原句；勿整节粘贴。
- 仍遵守「宁可少拆，不要硬造」：加厚已建质料，不靠多拆薄片凑数。

### 2.5 表/图必需槽

- `artifact-table` / `artifact-figure`：标题与编号、内容转写（或等价正文）；来源在 frontmatter `source`。
- 表：优先完整 Markdown 表；可附「关键观察」1–3 句及表注/原文说明摘录。
- 图：尽量保留轴含义、图注要点或作者对图的一句解释。

## 3. Card

### 3.1 frontmatter

必需：`id`、`title`、`type`、`maturity`、`lifecycle`、`domains`、`origin`、`sources`、`relations`、`created`、`updated`  
条件：`theory_status`、`superseded_by`

`id` 命名：汉字 / 字母 / 数字 / `-`；新建以中文为主；文件名 = `<id>.md`。

### 3.2 七型必需槽

| type | 必需语义槽（推荐标题） |
|---|---|
| domain | 核心问题, 边界, 内在张力, 原文摘录 |
| claim | 一句话主张, 依据, 已知限制, 原文摘录 |
| phenomenon | 模式描述, 典型实例, 反例与失效条件, 原文摘录 |
| model | 核心思想, 关键组件, 结构关系\|因果链条, 失效边界, 原文摘录 |
| method | 输入, 步骤, 输出, 适用边界, 原文摘录 |
| entity | 定义, 关键属性, 边界与局限, 来源, 原文摘录 |
| conflict | 对立双方, 核心分歧点, 各自证据/代价, 调和可能, 原文摘录 |

「限制/边界」承载：domain→边界；claim→已知限制；phenomenon→反例与失效条件；model→失效边界；method→适用边界；entity→边界与局限；conflict→调和可能。

缺槽：该节写 `原文未提及：……`。

### 3.3 槽同义

校验按语义槽识别，标题命中推荐或同义即满足。

## 4. Digest 产出类型

- 丰富 / 新建普通 Card
- domain 候选（聚类）
- conflict 候选（区分）
- relation / model 候选（衔接）
- 问题清单条目

硬纪律：有对立须提案 conflict（或说明为何不对立）；未经用户确认不得 apply。
