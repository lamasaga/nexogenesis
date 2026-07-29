---
version: "0.3.0"
updated: "2026-07-29"
---

# 正文结构契约（body-structure）

　　compile / digest / validate 共同引用的活契约。修改须经用户确认。机制说明见 `docs/2026-07-26-buffer-card-structure-draft.md`。

## 1. 两层分工

- **Buffer（质料层）**：**快节奏意义切片**——把杂乱原文切成消化时读起来舒服的块；极简 `role`；不定 Card `type`；不写 `id` / `relations`。质料是**滋养原料**，不是预售 Card。
- **Card（本体对象层）**：承诺维护的知识对象；须可独立阅读并解释某类问题。

**总原则**：用大模型聚合涌现知识结构。Compile 负责切舒服的原料；Digest 负责对着领域骨架 enrich（v3.1 手感）；Construct 负责在卡片网上发现/合并/升枢纽/张力。Harness 守闸门；思考留给模型。

结构涌现：

| 机制 | 落点 |
|---|---|
| 聚类 | `domain` Card + `domains` |
| 区分 | `conflict` Card + `conflicts-with` / `involves` |
| 衔接 | `relations`（默认）+ `model` / `method`（升格） |

## 2. Buffer

### 2.1 frontmatter（极简）

**LLM 输出建议只写**：`title`、`role`、`source`  
**落盘后 Harness 自动补**：`created`、`updated`、`status`（scratch）

磁盘上完整必填仍为：`title`、`role`、`created`、`updated`、`source`、`status`（校验用）。

可选（少用）：`genre`、`perspective`、`proposed_card_type`、`proposed_domains`、`related_within_batch`

禁止：`type`（七型）、`id`、`relations`；正文禁止 `[[ ]]`。

### 2.2 role 枚举

`meaning-unit`（默认）| `tension` | `link-hypothesis` | `profile-seed` | `detail` | `evidence` | `artifact-table` | `artifact-figure`

日常优先前三者；表图默认内嵌进 meaning-unit，少开 artifact。

目录：`05-Buffer/<role>/`

### 2.3 命名

文件名：`YYYY-MM-DD-HHMMSS-<序号>-<中文标题>.md`  
允许：汉字、字母、数字、连字符 `-`；禁止路径危险字符与空白。

### 2.4 正文（自由连贯，不强制四级槽）

　　意义切片正文用**自然段落**写清主张/机制、关键依据或数字、边界（若有）、1–2 条短摘录即可。

- **不要求** `### 核心表达 / 依据与细节 / 限制与边界 / 原文摘录`（旧式标题仍可识别，但不作闸门）。
- 空/近空正文 → 错误或 warning；`--strict-body` 将过短升为错误。
- 表图数字与观察默认写进所属块；仅例外单开 artifact，且须可读。
- 宁可少切，不要硬造；已切则宁厚勿空。

（兼容）旧式四级标题同义表仍保留在代码 `MEANING_UNIT_SLOTS`，供 substance 警告识别空心填槽，**不再**作为缺槽硬错误来源。

### 2.5 表/图（例外 role）

- `artifact-table` / `artifact-figure`：须有可独立阅读的转写与观察；否则应内嵌进 meaning-unit。
- 来源在 frontmatter `source`。

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

### 3.2.1 单卡可读（实质密度）

　　卡片是**可单独阅读并解释某类问题的意义单元**。槽位标题齐全不等于合格：

- 核心槽禁止几乎复读 `title`；须含可复述的机制或判断。
- 依据/实例禁止仅「原文未提及：具体依据」或「关联假设待检验」套话；无实质则勿建卡。
- 原文摘录应可核对；禁止空壳「原文未提及：摘录」。
- 图/表默认并入相关 model/claim 依据；独立 phenomenon 须有模式解读，非标题回声 + 裸表。
- `validate` / `doctor` 对空洞正文发 **WARNING**（不挡写入），digest 须从源头少产空心卡。

### 3.3 槽同义

校验按语义槽识别，标题命中推荐或同义即满足。

## 4. Digest 产出类型

- 丰富已有 Card（**默认优先**）
- 新建普通 Card（预算内）
- domain 候选（聚类）
- conflict 候选（区分）
- relation / model 候选（衔接）
- 问题清单条目

硬纪律：有对立须提案 conflict（或说明为何不对立）；未经用户确认不得 apply。

## 5. Construct 产出类型

- 发现冗余/分裂/错配 → 合并（superseded）或调整
- 升枢纽（entity / model）与语义边
- 张力升格（conflict + involves）
- 领域归属校准
