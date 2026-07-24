# ETP WebAgent 技术路线图

> 目标：把 v1.0 这套"markdown 文件 + AGENTS.md 手册 + 通用 LLM CLI 执行"的系统，逐步演化为一个**独立的 Web 应用**——有对话界面、图谱可视化、自动化心跳和代码级强制的行为闭环。
>
> 路线设计的第一原则：**每一步都产出可用的系统，而不是只有最后一步可用**。markdown 始终是事实之源（source of truth），代码与数据库只是索引、编排与界面。

---

## Phase 0：现状盘点（起点）

**架构实质**：
- markdown 文件系统 = 数据库；YAML frontmatter = schema（未强制）；git = 版本与可逆性；AGENTS.md = 用自然语言写的"程序"；Kimi Code 等 CLI agent = 运行时。
- 优点：零基建、可读、可 diff、与 LLM 天然亲和。
- 缺点（即 WebAgent 要解决的）：行为闭环靠纪律不靠强制；无并行能力；上下文窗口是硬约束；无界面（对话、确认、审批全在终端）；无定时心跳。

**Phase 0 的产出物即本仓库现状 + P0 脚本**（见手册 §九）。

---

## Phase 1：确定性基建（1–2 周）

**目标**：把手册 §九的脚本清单全部变成真实代码，pre-commit 全绿。

- 实现 `scripts/`：validate_buffer.py（含 author 字段）、validate_cards.py、append_journal.py、validate_theories.py、reflect_metrics.py；
- 为所有 frontmatter 写 **JSON Schema**（卡片/Buffer/理论/问题清单），校验器统一走 schema——这是后续所有代码化的地基；
- `hooks/pre-commit` 接入 git（`git config core.hooksPath hooks`）。

**验收**：一次故意埋错的 commit 被 pre-commit 拦下并给出可操作提示。

**技术选型**：Python 3.13 + PyYAML + jsonschema + click。无 Web 成分，纯本地。

---

## Phase 2：引擎编排层（2–4 周）★关键一跃

**目标**：把 AGENTS.md 里的指令流程从"自然语言程序"固化为**代码编排**，LLM 只负责语义判断。这是"行为闭环从纪律变成强制"的阶段，解决设计分析中的赌注 1。

核心组件：

```
etp/
├── engine/
│   ├── pipeline.py      # /compile /digest /construct 编排
│   ├── judge.py         # 六透镜判断引擎（见下）
│   ├── theorize.py      # 理论生命周期状态机
│   ├── reflect.py       # 心跳深反思 + 脱钩指标
│   └── distill.py       # 对话蒸馏（暂存→确认→入库）
├── llm/
│   ├── provider.py      # LLM 抽象层：OpenAI / Anthropic / 本地模型
│   └── structured.py    # 结构化输出（JSON mode / function calling）
├── cli.py               # etp compile / etp judge <id> / etp reflect ...
└── schemas/             # Phase 1 的 JSON Schema
```

三个技术要点：

1. **结构化输出替代自由文本解析**：所有 LLM 产物（Buffer 碎片、理论雏形、判断报告）以 JSON Schema 约束输出，由代码写入 markdown——消灭 frontmatter 格式漂移。
2. **lens_runner 真并行**：六透镜用 asyncio 并发调用，每个透镜独立 context（天然满足手册 §6.2"不许互相参考"），辩证综合在六份结果齐全后单独调用一次。成本约等于六次普通对话，可用小模型跑透镜、大模型跑综合来压缩费用。
3. **行为闭环代码强制**：`pipeline.construct()` 结束时自动调用 `judge.evaluate()` 与 `journal.append()`——闭环不再是 agent 的自觉，而是调用图的一部分。

**验收**：一条 `etp reflect` 命令自动完成：读日志 → 算指标 → 扫规律候选 → 生成报告 → 输出宪法提案草稿。

---

## Phase 3：Web 化（4–8 周）

**目标**：对话、确认、审批、浏览全部进入浏览器。

**架构**：

```
浏览器（React/Vue + 流式对话 + 图谱可视化）
   │  WebSocket / SSE
FastAPI 后端
   ├── 对话服务（带观点入场协议的代码实现）
   ├── 审批服务（蒸馏确认 / 宪法提案 / 理论转正）
   ├── 引擎调用（Phase 2 的 etp 包作为库）
   └── 索引层：SQLite（起步）→ Postgres（需要时）
        ※ markdown 仍是事实之源，DB 只是索引与缓存
```

**前端三个视图**：
1. **对话视图**（主界面）：流式对话 + 系统立场标注（"建构 X 视角"可点击跳转到理论档案）；
2. **知识视图**：卡片/理论/问题清单浏览器，理论生命周期看板（embryo→contested→growing 拖拽即审批）；
3. **图谱视图**：卡片 relations + 理论 competes-with 关系 → cytoscape.js / d3 力导向图；点击节点看证据基与失效边界。

**关键交互设计**：手册中的所有"确认"（蒸馏入库、宪法提案、理论转正/废弃）变成 **UI 审批流**——待办事项队列 + 一键批准/驳回/修改。这把 V0.5 的"确认瓶颈"从打断式问答变成异步收件箱。

**验收**：在浏览器里完成"对话 → 蒸馏 → 审批 → 入库 → 触发判断 → 理论看板可见"全闭环。

---

## Phase 4：GraphRAG 化（8–12 周）

**目标**：解决 v1.0 遗留的两个高优先级风险——上下文爆炸与入场质量。

1. **Embedding 索引**：卡片/碎片/理论/问题全部向量化（本地 bge / OpenAI embedding），入库时自动更新；
2. **图检索增强入场**：带观点入场协议从"规则式渐进阅读"升级为"语义检索 + 沿 relations 多跳扩展"——先向量召回种子，再沿图扩 1-2 跳，上下文预算内组装 Context Package；
3. **/construct 改造**：全量读取改为"图聚类 + 代表采样"，解决设计分析中的上下文爆炸遗留问题；
4. **仪表盘**：脱钩指标、价值轨迹、理论生态、问题清单活力的可视化（深反思从文本报告升级为实时面板）。

**技术选型**：向量库用 pgvector（若已上 Postgres）或 Qdrant/Chroma（独立部署）；图计算用 NetworkX 起步，规模上十万边再考虑 Neo4j。

**验收**：同一问题的对话入场质量（人工评估相关性）不低于规则式渐进阅读，且 token 消耗下降 ≥50%。

---

## Phase 5（可选）：多用户与部署

- 认证（单用户起步可用简单的 token 保护）；
- 个人库隔离：每个用户一个 git 仓库 + 独立索引命名空间；
- LLM key 管理（BYOK）与用量记账；
- 备份策略：git remote 即备份，DB 可从 markdown 全量重建（这是"markdown 为事实之源"架构的红利）。

---

## 数据模型演进路线

```
Phase 1:  YAML frontmatter（人工写）→ JSON Schema 校验
Phase 2:  JSON Schema 约束 LLM 输出 → 代码写 markdown
Phase 3:  markdown（事实之源）→ 增量同步 → SQLite 索引
Phase 4:  + 向量索引 + 图索引（皆可从 markdown 重建）
```

**不变量**：任何时候删掉全部代码与数据库，只留 markdown + git，系统信息零损失。这条不变量是选型的最高约束——任何让信息只存在于 DB 里的设计都一票否决。

---

## API 草图（Phase 3 核心端点）

```
POST /api/chat/stream            对话（SSE 流式，含入场协议）
GET  /api/inbox/approvals        待审批队列（蒸馏/提案/转正）
POST /api/approvals/{id}/decide  批准 / 驳回 / 修改
GET  /api/theories?status=       理论看板
GET  /api/graph?center=<id>      图谱子图（节点+边）
GET  /api/metrics                脱钩指标与健康仪表盘
POST /api/reflect                手动触发深反思
GET  /api/journal?date=          操作日志流
```

---

## 里程碑总览

| 阶段 | 周期 | 一句话交付 | 解决的核心风险 |
|---|---|---|---|
| P1 基建 | 1–2 周 | pre-commit 全绿 | V0.5"虚构基建"清算 |
| P2 编排 | 2–4 周 | 行为闭环代码强制 | 赌注 1（脱钩靠纪律） |
| P3 Web | 4–8 周 | 浏览器完成全闭环 | 确认瓶颈、无界面 |
| P4 GraphRAG | 8–12 周 | 检索增强 + 仪表盘 | 上下文爆炸、入场质量 |
| P5 部署 | 可选 | 多用户托管 | — |

**给未来执行者的第一条建议**：不要跳过 Phase 2 直接做 Phase 3。没有编排层的 Web 化只会得到一个漂亮的聊天框套着一堆纪律——那正是 V0.5 的病，换了个界面而已。

---

> *本路线图与 `V1.0/AGENTS.md`、`V1.0/设计分析与梳理.md` 构成 v1.0 三件套：手册定义系统，分析解释系统，路线图把系统变成软件。*
