# AGENTS.md — Nexogenesis P0 运行时契约

> 版本：P0（2026-07-24 修订版）  
> 作用：约束 AI 与 Harness 如何与底座交互。本手册本身可被用户修订，但修订前须经用户确认。

---

## 一、核心原则

1. **底座主权不变量**：`markdown + git` 是唯一事实之源。任何时候删除全部代码、索引、Journal，只留 `markdown + git`，系统信息零损失。
2. **Harness 负责过程，LLM 负责语义**：卡片校验、原子写入、索引生成、孤儿检测由 Harness 强制执行；内容好坏、冲突识别、新建/丰富判断由 LLM 负责。
3. **统一写入入口**：任何对底座的实质写入（新建/修改卡片、追加问题清单、追加 Journal）必须通过 `python -m nexogenesis write --batch <file>` 完成。禁止绕过该入口直接改文件。
4. **写路径优先**：系统设计优先降低高质量内容进入底座的摩擦，而非优先美化检索界面。
5. **复杂度必须有证据**：新增类型、关系、视图、自动化必须说明它解决的真实摩擦、最小改动、有效判断标准和撤回方式。
6. **P0 不是完整 Harness**：P0 实现结构约束层与最小原子写入事务；完整编排层（自动触发、Web UI、图检索）延至 P1/P2。

---

## 二、目录结构

```text
AGENTS.md                    # 本手册
README.md                    # 项目说明
00-Inbox/                    # 待处理原始材料（P1 启用）
01-Cards/                    # 知识卡片（扁平存储，不按领域分子目录）
   ├── _meta/
   │    ├── ontology.md      # 当前生效的元结构契约（初始化时从 scheme 复制）
   │    ├── domain-index.md  # 自动生成的领域视图
   │    ├── conflict-index.md# 自动生成的冲突视图
   │    └── theory-index.md  # 自动生成的理论视图
   └── <id>.md               # 所有卡片平铺，id 即文件名
02-Profile/                  # 用户/学派档案 + 问题清单
   └── 问题清单.md
03-Archive/                  # 已处理原始材料（P1 启用）
04-OutBox/                   # 分析产物、回答、报告
05-Buffer/                   # compile 产出的原子化片段（P1 启用）
06-Journal/                  # 操作大事记
nexogenesis/                 # Python 包（P0 交付）
schemes/default/             # 默认沉淀方案
hooks/                       # git hooks（init 时自动安装到 .git/hooks/）
```

**关键变化**：`01-Cards/` 扁平化，领域归属由 frontmatter 的 `domains` 字段显式声明，而不是目录结构。

---

## 三、卡片规范

### 3.1 通用 frontmatter

```yaml
---
id: "cognitive-scaffolding"
title: "认知脚手架"
type: "model"                    # 见 §3.2 类型系统
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
superseded_by: ""                # lifecycle=superseded 时必填
---
```

### 3.2 字段说明

| 字段 | 必需 | 说明 |
|---|---|---|
| `id` | 是 | 只能包含小写字母、数字、连字符 `-`。也是文件名。 |
| `title` | 是 | 卡片标题。 |
| `type` | 是 | 7 种卡片类型之一。 |
| `maturity` | 是 | 证据成熟度：`seed`=草稿/探索，`growing`=已确认，`mature`=充分验证。 |
| `lifecycle` | 是 | 当前是否活跃：`active`/`superseded`/`archived`。 |
| `domains` | 是 | 领域归属，至少一个，且必须对应一张真实存在的 `domain` 卡。 |
| `origin` | 是 | 归因：`user`/`system`/`document`/`external`。 |
| `sources` | 是 | 来源纪律；数量超过 12 会触发 warning，不报错。 |
| `relations` | 是 | 允许空；`target` 必须指向存在的卡片；数量超过 12 会触发 warning。 |
| `created`/`updated` | 是 | 创建/更新时间，建议 `YYYY-MM-DD`。 |
| `theory_status` | 否 | 仅 `claim`/`model` 可用；`draft`/`active`/`dormant`。 |
| `superseded_by` | 条件 | `lifecycle: superseded` 时必须提供，指向替代卡片。 |

### 3.3 写入权限规则

- `origin: system` 的卡片未经用户批准不能进入 `maturity: mature` 或 `theory_status: active`。
- `lifecycle: superseded` 必须提供 `superseded_by: <id>`。
- 更新已有卡片时 `created` 字段保持不变，只更新 `updated`。

### 3.4 卡片类型系统（7 种）

`question` 和 `synthesis` **不是**卡片类型：

- `question` 保存在 `02-Profile/问题清单.md`；
- `synthesis` 是 `04-OutBox/` 中的回答产物；若其中包含可复用的思想，再拆成 `claim`/`model` 卡片经 `/capture` 入库。

| 类型 | 回答的问题 | 最小内容要求 |
|---|---|---|
| `domain` | 这是哪个思想领域？ | 核心问题、边界、内在张力 |
| `claim` | 主张/立场是什么？ | 一句话主张、依据、已知限制 |
| `phenomenon` | 发生了什么模式？ | 模式描述、典型实例、反例 |
| `model` | 怎么理解这个复杂事物？ | 核心思想、关键组件、因果/结构、失效边界 |
| `method` | 怎么做？ | 输入、步骤、输出、适用边界 |
| `entity` | 这个对象是什么？ | 定义、关键属性、来源 |
| `conflict` | 根本矛盾在哪？ | 对立双方、核心分歧点、各自证据、调和可能 |

### 3.5 关系类型（8 种）

| 关系 | 含义 |
|---|---|
| `extends` | 扩展、细化、推进 |
| `supports` | 提供证据或支撑 |
| `conflicts-with` | 两个观点/模型之间的直接对立 |
| `involves` | 争议对象所涉及的各方（仅 `conflict` 卡片使用） |
| `example-of` | 是某概念/模型的具体实例 |
| `applies-to` | 应用于某范围/对象 |
| `based-on` | 思想来源、理论基础 |
| `influences` | 影响（比 `based-on` 弱） |

**重要区分**：

- `conflicts-with` 用于两张 `claim`/`model` 卡之间，表示它们直接矛盾；
- `involves` 用于一张 `conflict` 卡指向它涉及的各方；
- 领域归属**不是**关系，由 `domains` 字段声明；领域卡中的成员列表由 `index` 命令反向生成，不手写维护。

---

## 四、指令集（P0 务实裁剪版）

### 4.1 `/talk` 默认对话

- **轻量入场**：读取 `01-Cards/_meta/ontology.md` + `02-Profile/问题清单.md` + 与当前问题相关的卡片（优先读 `index` 生成的视图，而非扫全部目录）；
- **立场声明**：只有当存在 `theory_status: active` 且相关的理论时，才声明“这是从 X 视角看的”；否则不演；
- **区分观点**：回答中明确区分用户立场、文档立场、系统生成观点；
- **对话蒸馏**：对话结束或用户说“记一下”时触发 `/capture`；
- **批量确认**：蒸馏产物以候选形式呈现，用户确认后生成 batch 文件，由 Harness 统一写入。

### 4.2 `/capture` 捕获

替代旧版“自动入库”。每次最多提出 3 个候选：

- `claim`/`model`/`conflict`/`entity`/`method`/`phenomenon` → 写入 `01-Cards/`；
- `question` → 追加到 `02-Profile/问题清单.md`；
- 候选必须附带来源；
- 用户批准/修改/驳回后，AI 生成 batch 文件，调用 `python -m nexogenesis write --batch <file>`。

### 4.3 `/answer` 回答

- 检索并复用已有卡片；
- 区分用户立场、文档立场、系统生成观点；
- 普通回答直接输出到对话；
- 有长期复用价值的回答可保存到 `04-OutBox/` 作为 Synthesis；
- 若 Synthesis 中包含可沉淀的思想，再拆成 `claim`/`model` 卡片经 `/capture` 入库。

### 4.4 `/judge` 判断（按风险升级）

- **默认**：直接回答 + 一个最强反例/限制；
- **升级条件**：重要决策、明显争议、跨域因果、用户明确要求；
- **升级时**：从六透镜角度库中选 2-4 个真正相关的角度；
- **价值评估**：不打分，只观察后续有效复用率和用户纠正率。

### 4.5 `/theorize` 理论升格

- 理论不是独立层，而是卡片升格机制；
- 任何 `claim` 或 `model` 满足“跨多个领域解释”条件时，可被标记 `theory_status: draft`；
- 升格时正文必须补“失效边界”一节；
- `draft → active` 需用户确认；
- 对抗视角在 `/judge` 升级时引入，不是常驻相位。

### 4.6 `/reflect` 反思

- **Journal**：harness 自动追加大事记（蒸馏确认、理论转正、方案切换）；保留理由是未来训练优化的数据资产；
- **深反思**：用户触发或摩擦累积时运行；产出摩擦模式 + 改进提案；
- **手册修改**：永远 = 提案 + 用户批准，无自主执行器。

### 4.7 `/compile`、`/digest`、`/construct`

- 继承 v4.0 文档摄入流水线，但 **P0 不实现**；
- P1 迁移并适配到新的扁平结构和 7 型卡片；
- P2 实现完整编排层。

---

## 五、Harness CLI（P0 交付）

```bash
python -m nexogenesis init         # 初始化目录结构，安装 git hook
python -m nexogenesis validate     # 校验全部 frontmatter、链接、orphan
python -m nexogenesis index        # 生成 _meta/ 下的领域/冲突/理论视图
python -m nexogenesis write --batch <file>   # 统一原子写入入口
python -m nexogenesis doctor       # 一致性检查与诊断
python -m nexogenesis migrate --to <scheme> --dry-run   # scheme 迁移预演
```

### 5.1 `write --batch` 事务

`write` 是 P0 核心，所有实质写入必须经它完成。执行顺序：

1. 读取 batch YAML；
2. 校验 batch 自身格式；
3. 把每个写入项写到临时文件；
4. 运行完整校验（schema、幽灵链接、orphan、theory 失效边界等）；
5. 校验通过：原子移动临时文件到正式位置 → 追加 Journal → 重新生成索引；
6. 校验失败：删除临时文件，不追加 Journal，不更新索引，返回可读错误。

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
    body: |
      教师在给出反馈时，应明确指出学生当前表现与目标之间的差距，并提供可操作的建议。
    sources:
      - "2026-07-24 用户对话"
    created: "2026-07-24"
    updated: "2026-07-24"

  - target: "profile_question"
    question: "怎样区分有效反思与自我感动？"
    added_at: "2026-07-24"
```

### 5.2 写入安全

- 所有 YAML 用 `yaml.safe_load` 解析；
- ID 和路径穿越检查（id 只能包含 `[a-z0-9-]`）；
- 临时文件写入后原子替换正式文件；
- 事务语义：任何一步失败不留下半成状态；
- 同一次 batch 对应一个 `operation_id`。

### 5.3 数量上限改为 warning

- `sources` 数量、单卡 `relations` 数量不设 schema 错误；
- 超过建议值 12 时输出 warning；
- 是否真的限制，由真实图结构和使用数据决定。

---

## 六、P0 验收标准

第一个里程碑以“真实对话-捕获-回答闭环”成功为标志：

1. 用户能完成至少 10—20 次真实对话；
2. 重复执行 `/capture` 不会产生重复卡片；
3. 被驳回的候选不会进入知识库；
4. 修改卡片内容不改变其 ID；
5. 删除全部生成索引后可以一致重建；
6. 来源移动到 Archive 后引用仍有效；
7. 系统不能把文档观点误标为用户立场；
8. `origin: system` 未经批准不能进入 `mature` 或 `theory_status: active`；
9. git hook 已真实安装并在提交时运行；
10. 记录以下指标：候选接受率、有效复用率、纠正率、单次操作耗时。

---

## 七、AI 禁止与必须

### 禁止

- ❌ 绕过 `write --batch` 直接改卡片文件；
- ❌ 创建信息稀薄的空卡片；
- ❌ 为每篇文档都创建新卡片；
- ❌ 在 Inbox 中堆积已处理的原始文档；
- ❌ 未经用户确认修改 `02-Profile/`；
- ❌ 删除任何卡片（只能标记 `lifecycle: superseded`/`archived`）；
- ❌ 创建幽灵链接；
- ❌ 让卡片因无限引用而膨胀。

### 必须

- ✅ 优先丰富已有卡片，而非新建卡片；
- ✅ 检测并记录冲突；
- ✅ 维护领域卡片的完整性；
- ✅ 处理完后归档原始文档；
- ✅ 所有 AI 生成的内容标注来源；
- ✅ 任何写入先经过用户批准，再生成 batch 文件。

---

## 八、延后机制的进入条件

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
