---
version: "0.3.1"
updated: "2026-07-29"
---

# 正文结构契约（body-structure）

　　compile / digest / validate 共同引用的活契约。修改须经用户确认。机制说明见 `docs/2026-07-26-buffer-card-structure-draft.md`。

## 1. 两层分工

- **Buffer（质料层）**：Harness 按体裁开**阅读窗**，LLM 在窗内产出 **1～6** 个有命名、含质料的块；不定 Card `type`；不写 `id` / `relations`。质料供消化直接转入/并入 Card。
- **Card（本体对象层）**：承诺维护的知识对象；须可独立阅读，并满足类型语义槽。

**总原则**：Compile 保质料；Digest 骨架滋养并完成 Card 槽；Construct 发现/合并/枢纽/张力。Harness 守闸门；窗内切块与合并属 LLM。

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

磁盘上完整必填仍为：`title`、`role`、`created`、`updated`、`source`、`status`。

可选（少用）：`genre`、`perspective`、`proposed_card_type`、`proposed_domains`、`related_within_batch`

禁止：`type`（七型）、`id`、`relations`；正文禁止 `[[ ]]`。

### 2.2 role 枚举

`meaning-unit`（默认）| `tension` | `link-hypothesis` | `profile-seed` | `detail` | `evidence` | `artifact-table` | `artifact-figure`

日常优先前三者；表图默认内嵌。

目录：`05-Buffer/<role>/`

### 2.3 命名

文件名：`YYYY-MM-DD-HHMMSS-<序号>-<中文标题>.md`

### 2.4 阅读窗与正文

- **图书**：PDF 小节目录或 Markdown 二级/三级标题为窗；有子节时跳过粗章。
- **每窗 Buffer 数**：1～6，由内容与模型判断。
- 正文自由段落，保留机制/条件/关键数字/短摘录；**不强制**四级标题槽。
- 空/过短正文 → warning；`--strict-body` 升错误。

### 2.5 表/图（例外）

`artifact-*` 须可读；否则内嵌进 meaning-unit。

## 3. Card

### 3.1 frontmatter

必需：`id`、`title`、`type`、`maturity`、`lifecycle`、`domains`、`origin`、`sources`、`relations`、`created`、`updated`  
条件：`theory_status`、`superseded_by`

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

缺槽：写 `原文未提及：……`。消化时应尽量从 Buffer 转入可核对内容，避免空槽套话。

### 3.2.1 单卡可读

槽位齐全 ≠ 合格；核心禁止复读标题；依据须有机制或事实。`validate` 对空洞发 WARNING。

### 3.3 槽同义

按语义槽识别，标题命中推荐或同义即满足。

## 4. Digest

- 丰富已有 Card（默认）／新建（预算内）／domain／conflict／relation／问题清单
- Card 须满足类型槽；质料来自 Buffer 的转入与并入

## 5. Construct

- 发现冗余/分裂 → 合并（superseded）或调整
- 升枢纽与张力；补语义边
