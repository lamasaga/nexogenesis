---
version: "0.4.0"
updated: "2026-07-30"
---

# 正文结构契约（body-structure）

　　compile / digest / validate 共同引用的活契约。修改须经用户确认。  
　　写法正例：`.agent/reference/card-contracts/card-exemplars/`（方案源：`schemes/default/card-exemplars/`）。

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

### 3.2 结构即形式（开篇纪律）

　　**不要**给七型硬塞同一段「导读」。每种卡用自己的开篇槽；骨架本身就在编码对象类型。

| 开篇 | 适用 | 槽名 | 作用 |
|------|------|------|------|
| **诠释** | `domain` / `phenomenon` / `conflict` | `## 诠释` | 一段人话说清「这片领域 / 这套模式 / 这场对立」；再按该型展开 |
| **类型原生开篇** | `claim` / `model` / `method` / `entity` | 见下表 | 开篇已是命题或机制；再写诠释易与核心重复 |

　　`诠释` 为**强烈推荐**（digest 应写出）；校验不因缺诠释单独报错，以免阻断存量卡。新卡与 enrich 应以正例为准。

### 3.3 七型必需槽与推荐骨架

　　下列「必需」由 `validate` 硬校验；「推荐」写入正例与 digest，新卡应齐。

| type | 开篇 | 必需语义槽（推荐标题） | 推荐补槽 |
|---|---|---|---|
| domain | 诠释 | 核心问题, 边界, 内在张力, 原文摘录 | 领域肖像 |
| claim | 一句话主张 | 一句话主张, 依据, 已知限制, 原文摘录 | 立场/学派来源, 适用条件 |
| phenomenon | 诠释 | 模式描述, 典型实例, 反例与失效条件, 原文摘录 | — |
| model | 核心思想 | 核心思想, 关键组件, 结构关系\|因果链条, 失效边界, 原文摘录 | — |
| method | 输入 | 输入, 步骤, 输出, 适用边界, 原文摘录 | — |
| entity | 定义 | 定义, 关键属性, 边界与局限, 来源, 原文摘录 | — |
| conflict | 诠释 | 对立双方, 核心分歧点, 各自证据/代价, 调和可能, 原文摘录 | — |

缺必需槽：写 `原文未提及：……`。消化时应尽量从 Buffer 转入可核对内容，避免空槽套话。

推荐正文顺序（`##` 标题）：

```text
domain:      诠释 → 核心问题 → 领域肖像 → 边界 → 内在张力 → 原文摘录
phenomenon:  诠释 → 模式描述 → 典型实例 → 反例与失效条件 → 原文摘录
conflict:    诠释 → 对立双方 → 核心分歧点 → 各自证据或代价 → 调和可能 → 原文摘录
claim:       一句话主张 → 依据 → 已知限制 → [立场/学派来源] → [适用条件] → 原文摘录
model:       核心思想 → 关键组件 → 结构关系或因果链条 → 失效边界 → 原文摘录
method:      输入 → 步骤 → 输出 → 适用边界 → 原文摘录
entity:      定义 → 关键属性 → 边界与局限 → 来源 → 原文摘录
```

质控要点：

- **domain**：下属枢纽不能代替领域肖像；肖像写材料中的主要图像/分期/结构特征。  
- **claim**：一事一意；约超过 80 字或含两个以上独立判断 → 消化时建议拆卡或升 model。若代表学派立场，须在 `## 立场/学派来源` 中说明来源，并在正文中指出与对立立场的核心分歧。  
- **model**：组件写**职责**，勿名词子弹；「解释什么」写进核心思想首句，勿另套诠释。  
- **conflict**：核心分歧钉 **1～2** 处；`involves` 指向两造相关卡即可。  
- **phenomenon**：诠释给人听，模式描述给对照；二者勿逐句重复。  
- **区分三层声音**：写 `claim`/`model` 时，勿把「作者原意」「领域共识」「本库解读」混为一谈；需要时可显式标注。

### 3.3.1 单卡可读

槽位齐全 ≠ 合格；核心禁止复读标题；依据须有机制或事实。`validate` 对空洞发 WARNING。

### 3.4 槽同义

按语义槽识别，标题命中推荐或同义即满足。`诠释` 可识别同义「导读」（仅兼容旧卡；新卡用「诠释」）。

### 3.5 写法正例

　　见 `.agent/reference/card-contracts/card-exemplars/README.md`。digest 模仿正例，勿模仿电报式空心卡。

## 4. Digest

- 丰富已有 Card（默认）／新建（预算内）／domain／conflict／relation／问题清单
- Card 须满足类型槽；质料来自 Buffer 的转入与并入
- 开篇与骨架遵循 §3.2–3.3；对照 card-exemplars

## 5. Construct

- 发现冗余/分裂 → 合并（superseded）或调整
- 升枢纽与张力；补语义边
