# Buffer / Card 结构说明

> 状态：现行（2026-07-27）  
> 活契约：`01-Cards/_meta/body-structure.md`（校验与 prompt 以之为准）  
> 本文件是机制说明；改契约须先改 `body-structure.md` 并经用户确认。

---

## 1. 两层分工

| 层 | 是什么 | 回答的问题 | 身份 |
|---|---|---|---|
| **Buffer（质料层）** | 整理后的可重组材料 | 有什么意义、细节、证据、图表、张力、弱链？ | 无稳定 id；有 `source` + `role` |
| **Card（本体对象层）** | 承诺维护的知识对象 | 哪类对象？属哪些域？与谁关联？ | 有 `id` / `type` / `domains` / `relations` / `lifecycle` |

```text
00-Inbox（原始材料，处理前不可变）
  → compile：整理为质料（不定 Card type、不写死 relations）
  → 05-Buffer/<role>/
  → digest：跨源对照，提出候选（用户确认后写入）
  → 01-Cards + 02-Profile/问题清单
  → construct：跨批次结构扫描，先方案后写入
```

纪律：

- **`type` 只属于 Card**；Buffer 用 **`role`** 标注材料用途。
- compile **保细节、保张力、不和解、不定型**。
- 定型与关系承诺发生在 digest / construct，且须用户确认。

---

## 2. 结构涌现：聚类 / 区分 / 衔接

| 机制 | 结构操作 | 主要落点 | 升格门槛 |
|---|---|---|---|
| **聚类** | 同属一个问题空间 | `domain` Card + `domains` | 稳定问题 + 边界 + 内在张力 |
| **区分** | 不能同时成立或必须对照 | `conflict` Card + `conflicts-with` / `involves` | 可持续追踪的对立 + 双方证据 |
| **衔接** | 互相支撑、组成、延伸 | `relations`（默认）+ `model` / `method`（结构或步骤可复用时） | 组合关系本身值得维护时 |

衔接不另增 Card 类型：轻量用 `relations`；解释结构用 `model`；可执行步骤链用 `method`；质料侧种子为 `link-hypothesis`。

升格注意：

- 共同主题 ≠ domain。
- 局部差异 ≠ conflict。
- 两主张直接相斥可用 `conflicts-with`；冲突本身值得解释时另建 conflict，并用 `involves` 指向各方。

---

## 3. Buffer：质料层

### 3.1 颗粒度

**一文件 ≈ 一个意义单元，或一个独立表/图质料。**

成片闸门：

1. **单核**：只承载一个核心意义  
2. **自足**：脱离原文仍可读懂  
3. **可重组**：可被不同结构分别调用  
4. **留线索不锁结构**：弱关联标注，不写 Card relations  

同单元的依据、边界、摘录**内嵌**；禁止无核薄片。

### 3.2 `role`

| role | 含义 | 默认形态 |
|---|---|---|
| `meaning-unit` | 候选对象内核 | 独立文件；内嵌细节 |
| `detail` | 须被他处单独引用的细节 | 默认内嵌 |
| `evidence` | 可独立引用的关键证据 | 默认内嵌 |
| `artifact-table` | 重要表格 | 独立文件 |
| `artifact-figure` | 重要配图 | 独立文件 |
| `tension` | 未定型对立线索 | 独立文件 |
| `link-hypothesis` | 弱关联假设 | 可独立 |
| `profile-seed` | 风格/推理线索 | 分流 Profile，不进七型 Card |

目录：`05-Buffer/<role>/`。

### 3.3 frontmatter

必需：`title`、`role`、`created`、`updated`、`source`、`status`  
建议：`genre`、`perspective`  
可选：`proposed_card_type`、`proposed_domains`、`related_within_batch`

禁止：`type`（七型）、`id`、`relations`；正文禁止 `[[ ]]`（概念用 **加粗**）；禁止空质料与和稀泥式综合。

### 3.4 意义单元正文

| 槽位 | 强度 | 推荐标题 |
|---|---|---|
| 核心表达 | 必需 | `## 核心表达` |
| 依据与细节 | 必需 | `## 依据与细节` |
| 限制与边界 | 必需（无则「原文未提及」） | `## 限制与边界` |
| 原文摘录 | 必需 ≥1 | `## 原文摘录` |
| 观点分层 | 有混杂风险时必需 | `## 观点分层` |

### 3.5 表 / 图正文

必需：标题与编号、内容转写（表用 Markdown 表或结构化转写；图如实描述关键可见信息）。  
建议：支撑的意义单元标题、限制说明。  
一般不因表/图单独建 entity Card。

### 3.6 其他 role

- `tension`：双方、分歧点、各一侧依据、为何暂不定型  
- `link-hypothesis`：A/B、假设关系、强度、可证伪方式  
- `profile-seed`：观察与来源；不得写成用户稳定信念  
- `detail` / `evidence` 独立成文件时：说明为何不能内嵌及所属意义单元  

---

## 4. Card：本体对象层

### 4.1 frontmatter

`id`、`title`、`type`、`maturity`、`lifecycle`、`domains`、`origin`、`sources`、`relations`、`created`、`updated`；条件字段 `theory_status`、`superseded_by`。

- 更新保留原 `created`  
- `origin:system` 未经批准不得 `mature` / `theory_status:active`  
- `perspective:self → user`；`external → document`  

### 4.2 七型与判定优先级

`domain` | `claim` | `phenomenon` | `model` | `method` | `entity` | `conflict`

1. 根本对立 → `conflict`  
2. 可执行步骤 → `method`  
3. 解释结构/因果 → `model`  
4. 可观察模式 → `phenomenon`  
5. 主张/立场 → `claim`  
6. 有边界对象 → `entity`  
7. 思想领域 → `domain`  

主类型唯一；其余用 `relations` 连接。

### 4.3 通用纪律

- 限制/边界：七型全部必需（由各类型指定槽承载）  
- 原文摘录：至少 1 条，带精确锚点  
- 缺信息写 `原文未提及：……`，禁止空套话  

「限制/边界」承载：domain→边界；claim→已知限制；phenomenon→反例与失效条件；model→失效边界；method→适用边界；entity→边界与局限；conflict→调和可能。

### 4.4 命名与排版

- Buffer 文件名与 Card `id` 以中文为主：汉字 / 字母 / 数字 / `-`  
- Buffer：`YYYY-MM-DD-HHMMSS-<序号>-<中文标题>.md`  
- Card：文件名 = `<id>.md`；更新不改 `id`  
- 叙述段首两个全角空格（　　）  

### 4.5 各型最小骨架

**domain**：核心问题、边界、内在张力、原文摘录（成员由 index 反向生成）  
**claim**：一句话主张、依据、已知限制、原文摘录  
**phenomenon**：模式描述、典型实例、反例与失效条件、原文摘录  
**model**：核心思想、关键组件、结构关系/因果链条、失效边界、原文摘录  
**method**：输入、步骤、输出、适用边界、原文摘录  
**entity**：定义、关键属性、边界与局限、来源、原文摘录  
**conflict**：对立双方、核心分歧点、各自证据/代价、调和可能、原文摘录  

conflict 用 `involves`；claim/model 直接对立用 `conflicts-with`；二者不可互代。

### 4.6 内容变体（可选）

单卡建议 ≤3 个可选段；不得取代必需槽。例如：章节骨架、评测数据、课程阶段、立场演变、要点清单。若变体实为另一类型可独立回答的问题 → 拆卡。

---

## 5. role → 消化映射

| Buffer role | digest 默认动作 |
|---|---|
| `meaning-unit` | enrich 已有或新建 Card；`proposed_card_type` 仅供参考 |
| `artifact-table` / `artifact-figure` | 挂到相关 Card 依据/摘录 |
| `tension` | conflict 候选，或说明为何不对立；否则问题清单 |
| `link-hypothesis` | relation / model 候选；证据不足则跳过 |
| `profile-seed` | Profile / 问题清单，不进七型 Card |
| `detail` / `evidence` | 并入所属意义单元对应 Card 槽 |

优先 enrich；新建须离开原文仍可复用；禁止近义重复卡。

---

## 6. Digest / Construct 协议

### 6.1 Digest 入场

1. `ontology.md`  
2. 相关 domain 卡全文  
3. 候选实例卡（含正文或关键槽）  
4. 本批 scratch Buffer 全文  
5. 同批标题 / role 一览  
6. 问题清单  

### 6.2 Digest 产出（候选，须确认）

| 产出 | 机制 |
|---|---|
| 丰富 / 新建普通 Card | — |
| domain 候选 | 聚类 |
| conflict 候选 | 区分 |
| relation / model 候选 | 衔接 |
| 问题清单 | 开口 |

硬纪律：有对立须提案 conflict（或说明为何不对立）；未经确认不得 `--apply`。仅实际消费的 Buffer 标 `digested`。

### 6.3 Construct

跨批次扫描：

- 聚类：重复主题、假 domain、孤儿卡、领域边界漂移  
- 区分：未升格 tension、缺 conflict 卡或 `involves`  
- 衔接：链接空洞/过载、可抽成 model 的关系团、表图未挂上解释结构  

先出结构方案，后写入。

### 6.4 反模式

按维度切薄片；compile 定 type/relations；digest 只誊写不对照；自动抹平矛盾；用向量库/多 Agent 冒充发现。

---

## 7. Compile 要点

1. 按意义单元成片（过闸门）  
2. 重要表/图 → `artifact-*`  
3. 对立分片 + `tension`  
4. 可能联系 → `link-hypothesis`  
5. 细节内嵌  
6. 不写 Card 的 `type` / `id` / `relations`  

---

## 8. 校验与契约文件

- 活契约：`01-Cards/_meta/body-structure.md`  
- 写法正例：`01-Cards/_meta/card-exemplars/`（方案源 `schemes/default/card-exemplars/`）  
- Harness：`validate` 校验 Buffer `role` 与 Card `type`、语义槽、中文命名、幽灵链接等  
- 运行手册：`AGENTS.md`  
- Prompt：`schemes/default/prompts/`  

---

## 9. 模板

### Buffer 意义单元

```markdown
---
title: 示例主张标题
role: meaning-unit
created: "2026-07-27"
updated: "2026-07-27"
source: 《某材料》第×章
status: scratch
genre: essay
perspective: external
proposed_card_type: claim
---

## 核心表达

　　……

## 依据与细节

- ……

## 限制与边界

　　原文未提及：……

## 原文摘录

> 「……」
```

### Buffer 表格

```markdown
---
title: 表1 示例对照表
role: artifact-table
created: "2026-07-27"
updated: "2026-07-27"
source: 《某材料》表1
status: scratch
related_within_batch: [相关意义单元标题]
---

## 标题与编号

　　表1 示例对照表

## 内容转写

| 列A | 列B |
|---|---|
| …… | …… |

## 支撑的意义

　　服务于 **相关意义单元标题**。
```

### Card method

```markdown
---
id: 示例方法
title: 示例方法全称
type: method
maturity: growing
lifecycle: active
domains: [示例领域]
origin: document
sources:
  - 《某材料》第×章
relations: []
created: "2026-07-27"
updated: "2026-07-27"
---

## 输入

　　……

## 步骤

1. ……

## 输出

　　……

## 适用边界

　　……

## 原文摘录

> 「……」
```

---

## 10. 一句话

　　Buffer 用 role 整理质料；Card 用 type 承诺对象；结构靠聚类、区分、衔接三类协议涌现——compile 整理，digest 对照，construct 齐扫。
