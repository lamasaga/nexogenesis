# Nexogenesis 新一代知识-思维涌现系统设计（v2.0 修订稿）

> 本设计是 `NexogenesisV0.1/` 项目的起始 spec。它以被真实验证的 `思维涌现mainV4` 流水线为底座，融合 `NexogenesisV0.1/V1.0` 思维体器官的务实裁剪版，并回答两个关键问题：底座如何组织、思维体如何与底座协作。
> 
> 版本：2026-07-24 修订版
> 状态：设计稿，已根据首次审阅修订，待最终确认后进入 implementation plan

---

## 一、背景与目标

### 1.1 已被验证的资产

- `v3.1/v3.3/v4.0` 的 `compile → digest/construct` 流水线在个人思想沉淀场景中真实跑通；
- 领域卡片作为骨架、渐进式阅读、来源纪律、冲突一等公民、链接治理是有效约定；
- `v1.1` 的极简收缩给出了重要教训：**复杂度必须有真实使用证据支撑**。

### 1.2 长期目标

搭建一个"思维对话智能体"：以知识图谱沉淀一个人或一个学派的思想，支持对话、分析、反思、涌现与迭代，最终从 code-agent 模式过渡到独立的 harness 框架。

### 1.3 第一个里程碑（本期目标）

实现一个**真实可验证的对话-捕获-回答闭环**：

```text
用户对话
→ AI 提出不超过 3 个候选
→ 用户批准/修改/驳回
→ 统一 CLI 原子写入
→ 自动校验 + Journal + 索引更新
→ 后续提问检索并正确区分用户/文档/系统观点
```

文档批量摄取（`/compile` `/digest` `/construct`）放到第二个里程碑。

---

## 二、核心原则

### 2.1 底座主权不变量

`markdown + git` 是唯一事实之源。任何时候删掉全部代码、索引、数据库，只留 `markdown + git`，系统信息零损失。

图谱、向量索引、关系数据库都是**可重建索引**，永不持有不可替代的信息。

### 2.2 分工边界

- **Harness（代码）**：强制过程拓扑——所有写入走统一入口、schema 校验、权限检查、生成索引视图；
- **LLM（语义）**：判断内容好坏、识别冲突、生成卡片、组织论证。

Harness 不替代语义判断，语义判断不依赖"自觉"。

### 2.3 写入统一入口

任何对底座的实质写入（新建/修改卡片、更新 Profile、追加 Journal）都必须通过 `nexogenesis write` 完成。禁止 AI 或用户绕过该入口直接改文件。

### 2.4 写路径优先

历代最大瓶颈不是检索，而是**策展成本**——如何让高质量内容低摩擦地进入底座。新手册的每个机制都应优先服务于写路径。

### 2.5 复杂度必须有证据

任何新增机制（新类型、新关系、新视图、新自动化）必须说明：

- 它解决什么真实摩擦；
- 最小改动是什么；
- 怎么判断有效；
- 怎么撤回。

---

## 三、系统总架构

```text
┌─────────────────────────────────────────────────────────────┐
│ 思维体：对话 / 判断 / 理论 / 反思（LLM 负责语义判断）         │
├─────────────────────────────────────────────────────────────┤
│ Harness 编排层：统一写入入口、触发、校验、权限、视图生成      │
├─────────────────────────────────────────────────────────────┤
│ 沉淀方案层（Scheme）：可替换的策略包，本期只实现单方案可替换  │
├─────────────────────────────────────────────────────────────┤
│ 索引层（可重建）：图谱=思想结构 · RAG=细节语料 · DB=精确信息  │
├─────────────────────────────────────────────────────────────┤
│ 底座：markdown + git = 唯一事实之源                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、目录与存储结构

`NexogenesisV0.1/` 根目录：

```text
AGENTS.md                    # 系统手册（运行时契约）
README.md                    # 项目说明
00-Inbox/                    # 待处理原始材料（P1 启用）
01-Cards/                    # 知识卡片（扁平存储）
   ├── _meta/
   │    ├── ontology.md      # 当前生效的元结构契约
   │    ├── domain-index.md  # harness 生成的领域视图
   │    ├── conflict-index.md# harness 生成的冲突视图
   │    └── theory-index.md  # harness 生成的理论视图
   └── <id>.md               # 所有卡片平铺
02-Profile/                  # 用户/学派思想档案 + 问题清单
03-Archive/                  # 已处理原始材料（P1 启用）
04-OutBox/                   # 分析产物、回答、报告
05-Buffer/                   # compile 产出的原子化片段（P1 启用）
06-Journal/                  # 操作大事记
nexogenesis/                 # Python 包（P0 交付）
schemes/                     # 沉淀方案层
   └── default/              # 默认方案（v4.0 优化版）
        ├── scheme.md
        ├── genre-strategies.md
        └── ontology-template.md
hooks/                       # git hooks
V0.5/ V1.0/ V1.1/            # 历史版本档案（保留，只读）
```

**关键变化**：`01-Cards/` 扁平化，不再按领域分子目录。领域归属由 frontmatter 的 `domains` 字段显式声明。

---

## 五、卡片对象模型

### 5.1 通用 frontmatter

```yaml
---
id: "cognitive-scaffolding"
title: "认知脚手架"
type: "model"                    # 见 §6 类型系统
maturity: "growing"              # seed | growing | mature
lifecycle: "active"              # active | superseded | archived
domains:                         # 领域归属，≥1
  - "teaching"
  - "cognitive"
origin: "document"               # user | system | document | external
sources:
  - "《心智的构建》第 4 章"
relations:
  - target: "zone-of-proximal-development"
    type: "based-on"
    note: "脚手架作用在最近发展区内"
  - target: "self-regulated-learning"
    type: "supports"
    note: "拆除脚手架后的目标"
created: "2026-07-01"
updated: "2026-07-24"
theory_status: "active"          # 可选：draft | active | dormant
---
```

### 5.2 核心维度审计

| 字段 | 是否必需 | 作用 |
|---|---|---|
| id/title | 是 | 身份 |
| type | 是 | 阅读期待 + 最小内容校验 |
| maturity | 是 | 证据成熟度：seed=草稿/探索，growing=已确认，mature=充分验证 |
| lifecycle | 是 | 当前是否活跃：active/superseded/archived |
| domains | 是（≥1） | 渐进阅读入口 + orphan 检测 |
| origin | 是 | 归因：user / system / document / external |
| sources | 是 | 来源纪律 |
| relations | 是（允许空） | 推理路径 + 幽灵链接检测 |
| theory_status | 可选 | 跨领域理论升格标记 |

**写入权限规则**：

- `origin: system` 的卡片未经用户批准不能进入 `maturity: mature` 或 `theory_status: active`；
- `lifecycle: superseded` 必须提供 `superseded_by: <id>`，指向替代它的卡片。

**删除字段**：`strength`、`position` 与 `maturity`/`lifecycle` 重叠；`genre` 限制在 Buffer 阶段；`status` 拆分为 `maturity` + `lifecycle`。

---

## 六、卡片类型系统（7 种）

将原有 10 型按分类轴收束。`question` 和 `synthesis` **不是**卡片类型：

- `question` 保存在 `02-Profile/问题清单.md`；
- `synthesis` 是 `04-OutBox/` 中的回答产物；若其中包含可复用的思想，再拆成 `claim`/`model` 卡片。

| 类型 | 分类轴 | 回答的问题 | 最小内容要求 |
|---|---|---|---|
| `domain` | 结构 | 这是哪个思想领域？ | 核心问题、边界、内在张力 |
| `claim` | 认识论 | 主张/立场是什么？ | 一句话主张、依据、已知限制 |
| `phenomenon` | 认识论 | 发生了什么模式？ | 模式描述、典型实例、反例 |
| `model` | 认识论 | 怎么理解这个复杂事物？ | 核心思想、关键组件、因果/结构、失效边界 |
| `method` | 认识论 | 怎么做？ | 输入、步骤、输出、适用边界 |
| `entity` | 存在论 | 这个对象是什么？ | 定义、关键属性、来源 |
| `conflict` | 结构 | 根本矛盾在哪？ | 对立双方、核心分歧点、各自证据、调和可能 |

**合并说明**：

- `notion` + `principle` → `claim`（强度差异由正文表达，不再单独设类型）；
- `entity` + `group` → `entity`（"群体"是实体的基数属性，不是新类型）；
- `note` 删除，未成熟想法留在 `05-Buffer/`。

---

## 七、关系类型（8 种）

| 关系 | 含义 |
|---|---|
| `extends` | 扩展、细化、推进 |
| `supports` | 提供证据或支撑 |
| `conflicts-with` | 两个观点/模型之间的直接对立 |
| `involves` | 争议对象所涉及的各方（由 `conflict` 卡片使用） |
| `example-of` | 是某概念/模型的具体实例 |
| `applies-to` | 应用于某范围/对象 |
| `based-on` | 思想来源、理论基础 |
| `influences` | 影响（比 `based-on` 弱） |

**重要区分**：

- `conflicts-with` 用于两张 `claim`/`model` 卡之间，表示它们直接矛盾；
- `involves` 用于一张 `conflict` 卡指向它涉及的各方；
- 领域归属**不是**关系，由 `domains` 字段声明。

**冲突参与是逆视图**："某卡参与了哪些冲突"由 harness 从 `involves` 关系反向生成，不单独声明。

---

## 八、沉淀方案层（Scheme）

### 8.1 设计意图

让"如何沉淀和结构化"成为一种可替换的策略，而不是写死在手册里的常量。本期只验证"单方案可替换"，扩展场景（按语料类型、按建模对象）延后。

### 8.2 方案包结构

```text
schemes/default/
   scheme.md                  # scheme_id、版本、适用场景、设计意图
   genre-strategies.md        # 体裁识别规则 + 各体裁提取维度
   ontology-template.md       # 启用时生成的 _meta/ontology.md 模板
   profile-template.md        # Profile 档案模板
   migration.md               # 从其他 scheme 迁移的映射规则
```

### 8.3 方案切换流程

1. `python -m nexogenesis migrate --to <scheme_id> --dry-run` 生成迁移报告；
2. 报告包含：受影响的卡片列表、类型映射、关系映射、可能丢失的信息；
3. 用户批准后执行迁移；
4. 迁移前自动创建 git commit/tag；
5. 迁移后如不满意，可回滚到之前的 commit；
6. 不自动将不兼容卡片批量设为 `archived` 或 `deprecated`——默认保留原卡片，只在用户明确指示时替换。

### 8.4 默认方案

默认方案是 `v4.0` 优化版：保留 compile/digest/construct 流水线、分体裁编译、7 型卡片、8 种关系、渐进式阅读。

---

## 九、思维体指令集（务实裁剪版）

### 9.1 默认对话 `/talk`

- **轻量入场**：读 `ontology.md` + 问题清单 + 与当前问题相关的卡片；
- **立场声明**：只有当存在 `theory_status: active` 且相关的理论时，才声明"这是从 X 视角看的"；无相关理论时不演；
- **对话蒸馏**：对话结束或用户说"记一下"时触发；提取 user/system 观点、共识、未解决张力；
- **批量确认**：蒸馏产物以候选形式呈现，用户确认后生成 batch 文件，统一写入。

### 9.2 捕获 `/capture`

v1.1 的机制，替代 v4.0 "自动入库"。每次最多提出 3 个候选：

- `claim` → 写入 `01-Cards/`；
- `question` → 追加到 `02-Profile/问题清单.md`；
- `conflict` → 写入 `01-Cards/`（类型为 `conflict`）。

用户确认后，由 `nexogenesis write --batch` 统一写入。

### 9.3 判断 `/judge`（按风险升级）

- **默认**：直接回答 + 一个最强反例/限制；
- **升级条件**：重要决策、明显争议、跨域因果、用户明确要求；
- **升级时**：从六透镜角度库中选 2-4 个真正相关的角度；
- **价值评估**：不打分，只观察后续有效复用率和用户纠正率。

**砍掉**：construct 后强制六透镜评估、价值三维打分、生成问题计数。

### 9.4 理论 `/theorize`

理论不是独立层，而是卡片升格机制：

- 任何 `claim` 或 `model` 满足"跨多个领域解释"条件时，可被标记 `theory_status: draft`；
- 升格时正文必须补"失效边界"一节；
- `draft → active` 需用户确认；
- 对抗视角在 `/judge` 升级时引入，不是常驻相位。

### 9.5 反思 `/reflect`

- **Journal**：harness 自动追加大事记（蒸馏确认、construct、理论转正、方案切换）；保留理由是它是未来训练优化的数据资产；
- **深反思**：用户触发或摩擦累积时运行；产出摩擦模式 + 改进提案；
- **手册修改**：永远 = 提案 + 用户批准，无自主执行器。

**砍掉**：固定心跳、逐动作 git commit、轻反思每会话 3 行、脱钩指标阈值报警。

### 9.6 回答 `/answer`

检索并复用已有卡片，区分用户立场、文档立场、系统生成观点。

- 普通回答直接输出到对话；
- 有长期复用价值的回答可保存到 `04-OutBox/` 作为 Synthesis；
- 若 Synthesis 中包含可沉淀的思想，再拆成 `claim`/`model` 卡片经 `/capture` 入库。

### 9.7 文档摄入（P1/P2）

`/compile`、`/digest`、`construct` 继承 v4.0 流水线，但不在第一个里程碑实现：

- **P1**：迁移并适配 v4.0 编译器到新的扁平结构和 7 型卡片；
- **P2**：编排层——`construct` 完成自动触发可选判断与 journal。

---

## 十、Harness 工程地基

### 10.1 统一 CLI（P0 交付）

```bash
python -m nexogenesis init         # 初始化项目结构，安装 git hook
python -m nexogenesis validate     # 校验全部 frontmatter、链接、orphan
python -m nexogenesis index        # 生成领域/冲突/理论视图
python -m nexogenesis write --batch <file>   # 原子写入事务
python -m nexogenesis doctor       # 一致性检查与诊断
python -m nexogenesis migrate --to <scheme> --dry-run   # scheme 迁移预演
```

pre-commit 只调用 `python -m nexogenesis validate`。

### 10.2 `write --batch` 原子写入事务

`write` 是 P0 的核心，所有实质写入必须经它完成。同一 batch 中的写入项按 `id` 判断：id 不存在则创建，id 已存在则更新（更新时不改变 `created`）。执行顺序：

```text
1. 读取 batch YAML
2. 校验 batch 自身格式
3. 把每个写入项写到临时文件
4. 运行完整校验（schema、幽灵链接、orphan、theory 失效边界等）
5. 校验通过：
     - 原子移动临时文件到正式位置
     - 追加 Journal
     - 重新生成索引
6. 校验失败：
     - 删除所有临时文件
     - 不追加 Journal
     - 不更新索引
     - 返回可读错误
```

batch 文件示例：

```yaml
operation:
  id: "2026-07-24-143052-capture"
  source: "对话 2026-07-24"
  approved_by: "user"

writes:
  - target: "card"
    id: "feedback-gap-actionable"
    type: "claim"
    title: "教学反馈应优先指出可操作差距"
    domains: ["teaching"]
    origin: "user"
    maturity: "growing"
    lifecycle: "active"
    body: "..."
    sources:
      - "2026-07-24 用户对话"

  - target: "profile_question"
    question: "怎样区分有效反思与自我感动？"
    added_at: "2026-07-24"
```

### 10.3 写入安全（P0 必须实现）

- 所有 YAML 用 `yaml.safe_load` 解析；
- ID 和路径穿越检查；
- 临时文件写入后原子替换正式文件；
- 事务语义：任何一步失败，不留下半成状态；
- 写入失败时不追加 Journal、不更新索引；
- 同一次 batch 对应一个 `operation_id`。

### 10.4 数量上限改为 warning

- `sources` 数量、单卡 `relations` 数量不设 schema 错误；
- 超过建议值时输出 warning，供用户观察；
- 是否真的要限制，由真实图结构和使用数据决定。

### 10.5 P1/P2 延后

- **P1**：`compile`/`digest`/`construct` 文档摄入流水线；
- **P2**：完整编排层、图检索/向量索引、Web 界面；
- **P2+**：写锁、operation ID 持久化、提示注入防护、scheme 自动迁移执行器。

---

## 十一、关键数据流

### 11.1 对话-捕获闭环（P0）

```text
用户提问
   → /talk：轻量入场 + 直接回答（必要时风险升级调用 /judge）
   → 对话结束：/capture 提出 ≤3 候选
   → 用户批准/修改/驳回
   → AI 生成 batch 文件
   → nexogenesis write --batch
        → 临时写入 → 校验 → 原子提交 → Journal → 索引
   → 后续 /answer 检索复用
```

### 11.2 判断升级流

```text
对象（卡片/理论/问题）
   → 选择 2-4 个相关透镜角度
   → 各角度独立产出
   → 显式标注分歧
   → 定位结论
   → 直接输出到对话，或保存到 04-OutBox/
   → 若有可沉淀思想，经 /capture 入库
```

### 11.3 文档摄入流（P1）

```text
00-Inbox/raw
   → /compile（按 scheme 的体裁策略拆解为 Buffer）
   → /digest（增量消费 Buffer，丰富或新建卡片）
   → /construct（主题聚类、领域调整、Profile 更新）
   → Journal 记录
   → 03-Archive/
```

---

## 十二、验证与指标

第一个里程碑的验收标准：

1. 用户能完成至少 10—20 次真实对话；
2. 重复执行 `/capture` 不会产生重复卡片；
3. 被驳回的候选不会进入知识库；
4. 修改卡片内容不改变其 ID；
5. 删除全部生成索引后可以一致重建；
6. 来源移动到 Archive 后引用仍有效；
7. 系统不能把文档观点误标为用户立场；
8. `origin: system` 未经批准不能进入 `mature` 或 `theory_status: active`；
9. git hook 已真实安装并运行；
10. 记录以下指标：候选接受率、有效复用率、纠正率、单次操作耗时。

沿用 v1.1 的观察指标，**不设未经实验的健康阈值**。

---

## 十三、延后机制的进入条件

| 机制 | 进入条件 |
|---|---|
| 文档摄入流水线 | 对话-捕获闭环跑通且用户有真实文档需要处理 |
| 更多卡片类型 | 7 型在真实使用中持续无法表达 |
| 多透镜强制流程 | 简化判断反复遗漏关键风险 |
| 自动定期反思 | 人工 `/reflect` 经常被忘记且确实造成损失 |
| 图检索/向量库 | 文本检索在真实规模下明显失效 |
| Web 界面 | 文件与 code agent 成为主要使用障碍 |
| 多 Agent 分工 | 单流程出现可测的并发/隔离/专业化需求 |
| 自动优化手册 | 已有稳定评估集，人工改动效果可重复比较 |
| 联邦交换 | 至少两个真实用户需要交换结构化思想 |

---

## 十四、风险清单

| 风险 | 缓解 |
|---|---|
| 类型集从 10 收束到 7 后，真实归类更困难 | 先小规模试用，保留回迁到 10 型的可能性 |
| 扁平化后 AI 需读更多 frontmatter | P0 即实现 `index` 命令，AI 读生成视图而非扫目录 |
| `theory_status` 成为不被使用的装饰字段 | 初始不设默认值，只有用户/系统明确提升时才出现 |
| `write --batch` 事务实现过厚 | P0 先做最小原子事务，复杂批量回滚后移 |
| 用户过度依赖系统生成观点 | `origin: system` 必须显式标注；`claim` 默认视为探索性 |
| P0 仍无法强制人审环节 | 人审在对话/UI 层完成；`write` 只接受已批准的 batch |

---

## 十五、下一步

本 spec 最终确认后，进入 `writing-plans` 阶段，产出：

1. 新版 `AGENTS.md`；
2. `nexogenesis/` Python 包：
   - `validate`
   - `index`
   - `write --batch`（最小原子事务）
   - `init` + pre-commit hook 安装
3. 默认 Scheme 包；
4. 第一个里程碑的验收测试集。
