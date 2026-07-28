# AGENTS.md — Nexogenesis P0 运行时契约

> 版本：P0（2026-07-27）  
> 作用：约束 AI 与 Harness 如何与底座交互。本手册本身可被用户修订，但修订前须经用户确认。  
> Buffer / Card 正文结构以 `01-Cards/_meta/body-structure.md` 为准；机制说明见 `docs/2026-07-26-buffer-card-structure-draft.md`；**双轨检索**见 `docs/2026-07-27-retrieval-graph-rag-design.md`；**思维体注意力/STM**见 `docs/2026-07-28-thinking-body-attention-design.md`。

---

## 一、核心原则

1. **底座主权不变量**：约定目录下的 **markdown 是唯一语义事实之源**。任何时候删除全部代码与可重建索引（图、RAG、自动生成视图等），只留 markdown，知识内容零损失。**git 是强烈推荐的版本层**（历史、回滚、pre-commit），不是思想本体的必要条件；未启用 git 时不得声称操作已可逆。
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
00-Inbox/                    # 待处理原始材料
01-Cards/                    # 知识卡片（扁平存储）
   ├── _meta/
   │    ├── ontology.md      # 卡片类型与关系类型契约
   │    ├── body-structure.md# Buffer / Card 正文结构活契约
   │    ├── domain-index.md  # 自动生成的领域视图
   │    ├── conflict-index.md# 自动生成的冲突视图
   │    └── theory-index.md  # 自动生成的理论视图
   └── <id>.md               # 所有卡片平铺，id 即文件名
02-Profile/                  # 用户/学派档案 + 问题清单
   └── 问题清单.md
03-Archive/                  # 已处理原始材料
04-OutBox/                   # 分析产物、回答、报告
   └── discussions/          # 知识演进中的讨论文档（新生证据，入 RAG）
05-Buffer/<role>/            # compile 产出的质料（按 role 分目录）
06-Journal/                  # 操作大事记
nexogenesis/                 # Python 包
schemes/default/             # 默认沉淀方案
hooks/                       # git hooks（init 时安装到 .git/hooks/）
```

领域归属由 frontmatter 的 `domains` 字段声明；领域成员列表由 `index` 反向生成。

---

## 三、卡片规范

`type` 仅用于 Card。Buffer 使用 `role`，细则见 `body-structure.md`。

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
| `id` | 是 | 汉字、字母、数字、连字符 `-`；兼作文件名。新建以中文为主。 |
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

每次最多提出 3 个候选：

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

文档摄入三阶段。Buffer 为质料层（`role`），Card 为本体对象层（`type`）。结构涌现按聚类 / 区分 / 衔接三类协议进行。细则见 `body-structure.md` 与结构说明文档。

### 4.8 思维体体验层（对话面 · 闸门面 · 注意力）

　　细则见 `docs/2026-07-28-thinking-body-attention-design.md`；权重见 `schemes/default/attention.yaml`（可被 `.nexogenesis/attention.yaml` 覆盖）。

| 层 | 含义 | 落点 |
|----|------|------|
| 工具书 | 手边证据 | RAG |
| 长期记忆 | 已承诺结构 | 卡片图 |
| 短期记忆 | 约 10 次会话卷 | `.nexogenesis/memory/stm/`（非 Card） |
| 注意力 | 每轮 Working Set | `retrieve` 双账户：core / expansion / conflict |
| 强信号 | 偶发轻问 | `signal --text`；**捕获永远用户确认** |

- **默认对话面**：不要求用户点选 `/talk`/`/judge`；Agent 静默 `retrieve` + STM。  
- **闸门面**：捕获候选须用户批准后 `write --batch`；分析默认留在对话。  
- **强信号**：有可解释触发时轻问（记一下 / 可复用主张 / 对立 / Inbox→compile 建议等）；可用「先别记」关闭本会话主动捕获。  
- **会话覆盖**：`memory override --conflict N` 临时偏置席位，不改永久 YAML。

---

## 五、Harness CLI

　　对话指令（`/talk`、`/capture`、`/answer` 等）见 §四；本节为 **Harness 可执行命令** 的完整速查。几乎所有命令支持 `--root .`（项目根，默认当前目录）。更细的机制说明见 §八（摄入流水线）与 `docs/2026-07-27-retrieval-graph-rag-design.md`（双轨检索）。

### 5.0 CLI 命令速查

#### 底座维护

| 命令 | 常用选项 | 作用 |
|------|----------|------|
| `init` | `--root` | 初始化目录结构、复制 scheme 模板、安装 git pre-commit hook |
| `validate` | `--root` | 校验全部卡片 frontmatter、链接、orphan（pre-commit 亦调用） |
| `index` | `--root` | 生成 `01-Cards/_meta/` 下领域/冲突/理论视图 |
| `write` | `--batch <file>` `--root` | **统一原子写入入口**（卡片、问题清单、Journal）；成功后自动 `index` + `graph rebuild` + `rag index` |
| `doctor` | `--root` | 目录/契约/hook 检查 + `validate` + 图/RAG 索引陈旧 WARNING |
| `migrate` | `--to <scheme>` `--dry-run` `--root` | scheme 迁移预演 |

#### 文档摄入：`compile` → `digest` → `construct`

| 命令 | 常用选项 | 作用 |
|------|----------|------|
| `compile` | `--plan` | 预览 Inbox 分波计划（不写 prompt） |
| | `--root` | 生成本波 compile prompt 到 `.nexogenesis/tmp/compile/` |
| | `--check-responses` | 检查 `batch-*-response.*` 格式（不写盘） |
| | `--apply` | 将 response 落盘为 `05-Buffer/`（按文件部分成功） |
| | `--response <file>` | 只检查/apply 指定 response |
| | `--all` `--recursive` `--deep` | 关闭分波 / 递归扫 Inbox / 深度模式（每波 1 篇） |
| | `--max-chars` `--wave-prompts` `--wave-docs` | 分波规模控制 |
| | `--genres "a.md=paper,..."` | 体裁覆盖 |
| | `--strict-body` | 语义槽缺失升为错误 |
| `digest` | `--plan` | 预览本波 Buffer 选择与字符预算 |
| | `--root` | 生成本波 digest prompt（默认 `status=scratch`，分波） |
| | `--apply` | 应用 `.nexogenesis/tmp/digest/batch.yaml` 写入卡片 |
| | `--auto` | 无 batch → prompt+规程；有 batch → 自检通过后 apply |
| | `--wave-buffers N` `--deep-cards N` | 本波 Buffer 数 / 深读卡数 |
| | `--status scratch` `--all-scratch` | Buffer 状态过滤 / 调试全量 |
| `construct` | （默认） | 结构诊断：`lenses-report.md` + graph analyze + `structure-ops-draft.md` |
| | `--diagnose` | 显式只诊断（同默认） |
| | `--lens cluster\|distinguish\|articulate\|cross_source` | 单镜头 prompt（禁止 `all`） |
| | `--plan` | 预览本镜头深读对象 |
| | `--apply` | 应用 `.nexogenesis/tmp/construct/batch.yaml` |
| | `--auto` | 无 lens → 诊断+suggested-lenses；有 lens+batch → 自检 apply |
| | `--auto --lens <name>` | 单镜头自主模式 |
| | `--deep-cards N` `--wave-buffers N` | 镜头模式深读规模 |

**摄入典型顺序**（Agent 串行，中间产物保留在 `.nexogenesis/tmp/`）：

```bash
python -m nexogenesis compile --plan --root .
python -m nexogenesis compile --root .
# → LLM → batch-XXX-response.md → compile --check-responses → compile --apply

python -m nexogenesis digest --plan --root .
python -m nexogenesis digest --root .
# → LLM → batch.yaml → digest --apply  或  digest --auto（自检后 apply）

python -m nexogenesis construct --root .
# → 读 lenses-report / suggested-lenses → construct --lens <name> → batch.yaml → construct --auto --lens <name>
```

#### 双轨检索：结构图 + 质料 RAG

| 命令 | 常用选项 | 作用 |
|------|----------|------|
| `graph rebuild` | `--root` | 从卡片重建结构图索引（`.nexogenesis/graph/`） |
| `graph stats` | `--root` | 节点/边统计 |
| `graph analyze` | `--rebuild` `--root` | orphan、conflict 缺口、桥接点 → `structure_ops.json` + 报告 |
| `graph retrieve` | `--query` `--seed`（可多次） `--hops` `--max-nodes` `--out` | 结构子图检索，写入 Context Package |
| `graph export` | `--center <id>` `--hops` `--out` `--rebuild` | 导出 GraphML（默认 `.nexogenesis/tmp/graph/graph.graphml`） |
| `rag index` | `--full` `--kinds` `--root` | 建/增量更新 FTS 索引（默认增量；`--full` 全量） |
| `rag stats` | `--root` | 语料块数与索引时间 |
| `rag search` | `--query` `--kinds` `--top` `--root` | 质料检索（archive/buffer/discussion/outbox/card_excerpt） |
| `retrieve` | `--query` `--mode talk\|answer\|digest\|construct\|judge` | **统一双轨入口**：结构子图 + RAG 质料 → Context Package（默认注意力双账户） |
| | `--seed` `--budget-chars` `--graph-hops` `--graph-nodes` `--rag-top` | 种子卡 / 预算 / 图与 RAG 规模 |
| | `--no-graph` `--no-rag` `--no-attention` `--no-stm` `--print-yaml` `--out` | 禁用轨/注意力/STM / 打印 / 输出 |
| `memory start\|status\|update\|override\|end` | `--focus` `--cite` `--tension` / `--conflict N` | 短期记忆会话卷与临时席位覆盖 |
| `attention show\|validate` | `--profile` `--print-yaml` | 查看/校验注意力 YAML 有效配置 |
| `signal` | `--text` `--bump-turn` | 强信号评估（只建议，不写卡） |

**检索典型用法**：

```bash
python -m nexogenesis graph rebuild
python -m nexogenesis rag index          # 增量；rag index --full 全量重建
python -m nexogenesis memory start --title "今日对话"
python -m nexogenesis retrieve --query "…" --mode talk --root .
python -m nexogenesis signal --text "记一下"
```

　　`write --batch` 成功后 Harness 自动：`index` → `graph rebuild` → `rag index`（增量）。`doctor` 会提示图/RAG 索引是否落后于 markdown。

#### 速记（一行版）

```bash
python -m nexogenesis init | validate | index | doctor
python -m nexogenesis write --batch <file>
python -m nexogenesis compile [--plan|--check-responses|--apply]
python -m nexogenesis digest [--plan|--apply|--auto]
python -m nexogenesis construct [--lens|--apply|--auto]
python -m nexogenesis graph rebuild|stats|analyze|retrieve|export
python -m nexogenesis rag index|stats|search
python -m nexogenesis retrieve --query "…" --mode talk
python -m nexogenesis memory start|status|update|override|end
python -m nexogenesis attention show|validate
python -m nexogenesis signal --text "…"
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
- ID 与路径穿越检查（id 允许汉字、字母、数字、连字符 `-`，禁止路径分隔符与危险字符）；
- 先写入 staging 并完整校验，通过后才提交到正式位置；失败不留下半成卡片或问题清单；
- `origin: system` 进入 `mature` / `theory_status: active` 须 `approved_by: user` 且 `operation.allow_system_promotion: true`；
- 同一次 batch 对应一个 `operation_id`；digest/construct 用 `operation.consumed_buffers` 声明实际消费的 Buffer 路径。

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
- ✅ 任何写入须经授权：逐步确认，或用户一句「开始消化/建构」/`--auto` 视为本轮授权；中间产物仍保留在 `.nexogenesis/tmp/`。

---

## 八、文档摄入流水线

　　CLI 完整参数见 **§5.0**；以下为编排纪律与机制说明。

```bash
python -m nexogenesis compile --plan --root .    # 预览分波计划
python -m nexogenesis compile --root .           # 生成本波 prompt（默认自动分波）
# Agent 串行调用 LLM，保存 response 到 .nexogenesis/tmp/compile/batch-XXX-response.md
python -m nexogenesis compile --check-responses  # 落盘前检查（推荐每写完一个就跑）
python -m nexogenesis compile --apply --root .   # 按文件部分成功写入 Buffer

python -m nexogenesis digest --plan --root .     # 预览本波 scratch 与深读卡
python -m nexogenesis digest --root .            # 生成 digest prompt（分波，非全库）
# Agent 调用 LLM，保存 batch 到 .nexogenesis/tmp/digest/batch.yaml
python -m nexogenesis digest --apply --root .    # 写入 01-Cards/，标记 Buffer 为 digested
# 或 Agent 自主：digest --auto →（写 batch）→ digest --auto（自检后 apply）

python -m nexogenesis construct --root .         # 默认：结构诊断（无全文）
python -m nexogenesis construct --lens distinguish --root .
# Agent 保存 batch 到 .nexogenesis/tmp/construct/batch.yaml
python -m nexogenesis construct --apply --root . # 结构优化；可标记 digested → constructed
# 或：construct --auto → 按 suggested-lenses 逐镜 construct --auto --lens …
```

### 8.1 `/compile`

- 扫描 `00-Inbox/` 中的 `.md`、`.txt`、`.markdown`、`.pdf`（默认不递归；`--recursive` 可扫子目录）；
- 启发式预判体裁：`book` / `paper` / `essay` / `dialogue` / `scrap` / `generic`；
- **默认自动分波**：按库存选择本波文档（默认约 ≤5 篇 / ≤4 个 prompt），其余留 Inbox；`--all` 关闭分波；`--plan` 预览；
- 默认每批约 **10000** 等效中文字（`--max-chars` 可覆盖）；同批按体裁装箱，`scrap` 最多混 3 源，`paper`/`book` 等不混装；
- 生成体裁专属 prompt 到 `.nexogenesis/tmp/compile/`，并写 `wave-manifest.json`；
- LLM 按**意义单元**整理质料，用 `role` 标注（`meaning-unit`、`artifact-table`、`artifact-figure`、`tension`、`link-hypothesis`、`profile-seed` 等）；
- 不定 Card `type`，不写 `id` / `relations`；对立不和解；细节内嵌；
- response **必须**命名为 `batch-XXX-response.md`（或 `.yaml`），与 prompt 序号对应；草稿 `*-blocks.md` / `*-fragments.json` 非正式格式；
- **编排纪律**：默认单代理串行生成 response；勿并行子代理。每写完一个先 `compile --check-responses`；禁止手写脚本「大修」response，不合格则重生成该 batch；
- `--apply` 按 **response 文件**独立落盘（部分成功保留失败文件）；`--response <file>` 只处理一个；语义槽缺失默认 warning（`--strict-body` 升为错误）；
- `--apply` 在本波全部 batch 成功后，才归档已完成全部单元的原文；长书可跨多波，进度记在 `progress.json`。

### 8.2 `/digest`

- **先消化、后建构**；默认只处理一波 `status: scratch`（`--wave-buffers` 默认 8），其余留待下波。
- 上下文：全库**卡片目录**（无正文）+ **相关深读卡正文**（`--deep-cards` 默认 6，优先 graph retrieve）+ 本波 Buffer 全文 + 问题清单；可附 `_meta` 索引摘录与 **RAG 质料摘录**（archive/buffer/discussion，nascent 不得升格为 Card）。
- 空库/无 domain：batch **必须先写 domain**，再建实例卡（`domains` 仅引用本批或已有 id）。
- 跨源对照发生在同波内；产出 enrich/新建 Card、domain/conflict/relation/model 候选、问题清单。
- `--plan` 预览本波选择与字符估算；`--all-scratch` 仅调试。
- `--apply` 经 `write --batch` 写入，并把 `consumed_buffers` 标为 `digested`。
- **`--auto`**：无 `batch.yaml` 时生成 prompt + `auto-runbook.md`；有 batch 时 Harness 自检（YAML、必填字段、`consumed_buffers`、bootstrap domain）通过后戳记 `approved_by: agent`（已是 `user` 则保留）并 apply。不调用 LLM。

### 8.3 `/construct`

- 在已有卡片网上做结构校准（勿在空库上优先于 digest）。
- **默认 `--diagnose`**：Harness 结构信号 + **graph analyze**（orphan/conflict 缺口/桥接点）+ 卡目录 + Buffer 索引（**无全文**）→ `lenses-report.md`；并写 `structure-ops-draft.md`。
- **`--lens`**：一次只跑一个镜头（`cluster` / `distinguish` / `articulate` / `cross_source`）；注入目录 + 点名深读卡/Buffer。禁止 `all`。
- 产出仍是 `write --batch` 候选；确认后 `--apply`；可将声明消费的 `digested` Buffer 标为 `constructed`。
- **`--auto`**（无 lens）：诊断 + `suggested-lenses.txt` + `auto-runbook.md`。  
  **`--auto --lens <name>`**：无 batch 则生成该镜头 prompt+规程；有 batch 则自检后 apply（同 digest 戳记规则）。
- GraphML 导出：`python -m nexogenesis graph export`（可选 `--center`/`--hops` 子图）；P0 图即卡片 + relations + `index` 投影。

### 8.4 人机协作边界

- 默认命令只生成 prompt/batch，**不自动写入卡片**（须 `--apply` 或 `--auto` 二次通过自检）。
- **逐步模式**：Agent 在 `--apply` 前检查产物，`operation.approved_by` 记 `user`。
- **自主模式**：用户说「开始消化/建构」或显式 `--auto` = 本轮写入授权；Agent 自审中间产物并循环至自检通过；`approved_by` 通常为 `agent`；tmp 下 prompt/batch/报告**一律保留**供事后分析。
- 未经用户批准，不得把 `origin: system` 的产出直接标为 `mature` 或 `theory_status: active`（`--auto` 自检亦拒绝此类升格）。

---

## 九、双轨检索：结构图 + 质料 RAG

> 细则见 `docs/2026-07-27-retrieval-graph-rag-design.md`。本节为运行时摘要。

### 9.1 分工

- **结构轨（Graph）**：`01-Cards` 关系网——论证骨架、领域、冲突、显式 `relations`；索引在 `.nexogenesis/graph/`，可重建。
- **质料轨（RAG）**：原文、Buffer 片段、归档、**讨论文档（新生证据）**——细节与证据；语料仍在 markdown，索引在 `.nexogenesis/rag/`，可重建。
- **统一入口**：`python -m nexogenesis retrieve --query … --mode talk|digest|answer|construct` → Context Package（结构区 + 质料区 + 归因）。

### 9.2 新生证据（discussion）

- 路径：`04-OutBox/discussions/YYYY-MM-DD-<主题>-discussion.md`。
- 性质：知识演进中的讨论纪要；RAG 中 `attribution: nascent`；**不自动**升格为 Card。
- 升格：讨论中可维护的主张经 `/capture` 或 digest → `write --batch`；discussion 文件保留并补 `linked_cards`。

### 9.3 检索纪律

- RAG 命中**不得**直接写入 `relations` 或新建 Card。
- Context 必须区分：`structure`（图）与 `material`（RAG），并标注 `user` / `document` / `system` / `nascent`。
- `write --batch` 成功后顺序：`index` → `graph rebuild` → `rag index`（增量）。

### 9.4 与指令的关系

| 指令 | 结构轨 | 质料轨 |
|------|--------|--------|
| `/digest` | graph retrieve 深读卡 | buffer 全文 + RAG 质料摘录（archive/discussion） |
| `/construct` | graph analyze + structure_ops 合并进诊断 | 低权重 |
| `/talk` `/answer` | 子图 + 立场卡片 | 引文与讨论块 |
| `/compile` | — | 产出 buffer → 入 RAG 语料 |

---

## 十、延后机制的进入条件

| 机制 | 进入条件 |
|---|---|
| 文档摄入流水线 | 已有真实文档需要处理 |
| 更多卡片类型 | 7 型在真实使用中持续无法表达 |
| 多透镜强制流程 | 简化判断反复遗漏关键风险 |
| 自动定期反思 | 人工 `/reflect` 经常被忘记且确实造成损失 |
| **图检索（G1）** | R0/R1 实现完成，且卡片 ≥20 或 digest 深读明显漏召回 |
| **质料 RAG（FTS）** | R2 实现完成；有 archive/buffer/discussion 语料 |
| **向量 / 混合 RRF** | 黄金集证明 FTS+图遍历不够 |
| Web 界面 | 文件与 code agent 成为主要使用障碍 |
| 多 Agent 分工 | 单流程出现可测的并发/隔离/专业化需求 |
| 自动优化手册 | 已有稳定评估集，人工改动效果可重复比较 |
| 联邦交换 | 至少两个真实用户需要交换结构化思想 |
