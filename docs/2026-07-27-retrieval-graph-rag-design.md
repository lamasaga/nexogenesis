# 双轨检索设计：结构图 + 质料 RAG

> 状态：P1 基线 + R5/R7 已落地（2026-07-27）；R6 向量层延后  
> 活契约：`AGENTS.md` §十（摘要）；本文件为机制说明。  
> 前提：约定目录下的 **markdown 为唯一语义事实之源**；图索引与 RAG 索引均可删除并自 markdown 重建。git 为推荐版本层，不是语义权威。

---

## 1. 设计目标

　　Nexogenesis 的终局不是「能搜到的文档库」，而是：

1. **知识结构**：卡片 + 关系 + 领域，可校验、可演进；
2. **思维体**：在用户沟通、分析、反馈中，带立场地使用结构并**提出结构变更**；
3. **质料补充**：细节、原文、图表、对话片段等**不强行全部升格为卡片**，但以可检索方式保留，为结构与判断提供证据。

　　检索层必须同时服务 **读（talk / answer / digest）** 与 **写（结构优化提案）**，且不把 RAG 召回结果误当作已确认的结构事实。

---

## 2. 核心分工：图负责结构，RAG 负责质料

```text
                    ┌─────────────────────────────────────┐
                    │           用户问题 / 任务              │
                    └──────────────────┬──────────────────┘
                                       │
              ┌────────────────────────┴────────────────────────┐
              ▼                                                 ▼
   ┌──────────────────────┐                       ┌──────────────────────┐
   │  结构轨（Graph）       │                       │  质料轨（RAG）         │
   │  01-Cards 关系网       │                       │  可重建语料库          │
   │  · 节点 = Card         │                       │  · 原文 / 片段 / 讨论  │
   │  · 边 = relations 等   │                       │  · 细节与「新生证据」  │
   └──────────┬───────────┘                       └──────────┬───────────┘
              │ 种子 + 多跳子图                               │ 按 query / 卡片锚点召回
              └────────────────────┬──────────────────────────┘
                                   ▼
                    ┌──────────────────────────────┐
                    │  Context Package（统一上下文包）  │
                    │  · 结构区：卡片摘要 + 关系路径    │
                    │  · 质料区：RAG 块 + 来源锚点      │
                    │  · 归因：user / document / system │
                    │           / nascent（新生证据）   │
                    └──────────────┬───────────────────┘
                                   ▼
                              LLM 推理
                                   ▼
                    write --batch（仅结构变更经此落盘）
```

| 维度 | 结构轨（Graph） | 质料轨（RAG） |
|------|-----------------|---------------|
| 事实地位 | 已承诺维护的知识对象 | 证据与细节；默认**不**自动升格为 claim |
| 存储 | `01-Cards/*.md` | 语料仍落在 markdown 目录；向量/FTS 在 `.nexogenesis/rag/` |
| 检索方式 | 种子 + 图遍历 + 关系类型策略 | 关键词 / 向量 / 混合；**必须**带文件锚点 |
| 主要用途 | 论证骨架、领域、冲突、关系 | 原文摘录、表图、对话、讨论纪要 |
| 写回 | `write --batch` 改卡片 | 新语料**追加文件或归档**；索引 `rag index` 重建 |

　　**纪律**：RAG 命中不得直接写入 `relations`；若值得长期维护，须走 digest / capture → batch。

---

## 3. 语料分层：什么进入 RAG

　　未来所有资料经底座拆解后：**结构进图，质料进 RAG**。来源类型用 `corpus_kind` 标注（写入索引 manifest，不新增卡片类型）。

| corpus_kind | 物理位置 | 何时入 RAG | 与图的关系 |
|-------------|----------|------------|------------|
| `archive` | `03-Archive/` | compile 归档后 | 卡片 `sources` 可指向此路径 |
| `buffer` | `05-Buffer/<role>/` | compile apply 后（可选 digested 后） | 无 id；digest 消费后仍保留全文可检 |
| `outbox` | `04-OutBox/` | 用户保存的分析 / Synthesis | 可引用卡片 id 列表 |
| `discussion` | `04-OutBox/discussions/` | 知识演进中的讨论文档（见 §4） | **新生证据**；可 `linked_cards: []` |
| `journal` | `06-Journal/` | 仅索引操作摘要行（非全文默认） | 审计迹，低优先级召回 |
| `card_excerpt` | 由 Harness 从 Card 正文切出 | `graph rebuild` 时同步 | 与图节点 `card_id` 绑定，便于「结构→质料」跳转 |

　　**不进入 RAG 的**：`00-Inbox/` 未处理原文（避免与 compile 重复）；`_meta/` 生成视图（由 graph/index 服务）。

### 3.1 切块（chunk）规则

| 来源 | 切块策略 | 元数据必填 |
|------|----------|------------|
| archive 长文 | 按章节 / 段落，≤1500 等效中文 | `source_file`, `section`, `page` |
| buffer | **一片一 chunk**（已是意义单元） | `buffer_path`, `role`, `status` |
| discussion | 按标题 / 议题段 | `discussion_id`, `date`, `origin` |
| card_excerpt | 按 `##` 节 | `card_id`, `section` |

　　每 chunk 在 manifest 中有稳定 `chunk_id`（由路径 + 偏移哈希），内容变更则 id 变，旧向量由 `rag index` 垃圾回收。

---

## 4. 「新生证据」：讨论文档生命周期

　　知识演进过程中产生的讨论（对话纪要、研讨记录、用户与 Agent 的结构化讨论导出）作为 **nascent（新生）** 质料，**补充**结构图，不替代卡片。

### 4.1 存放约定

```text
04-OutBox/discussions/
  YYYY-MM-DD-<主题>-discussion.md
```

建议 frontmatter：

```yaml
---
id: "2026-07-27-反馈差距研讨"
title: "反馈差距与自我感动的边界讨论"
kind: discussion          # 固定 discussion
origin: user              # user | system | mixed
status: active            # active | superseded | archived
linked_cards:             # 讨论涉及的卡片（可空，后补）
  - "教学反馈应指出可操作差距"
linked_questions:         # 可选，对应问题清单
  - "怎样区分有效反思与自我感动？"
sources:
  - "Cursor 对话 2026-07-27"
created: "2026-07-27"
updated: "2026-07-27"
---
```

### 4.2 生命周期

```text
对话 / 研讨
  → 用户或 Agent 整理为 discussion.md（可 /capture 前先落 OutBox）
  → rag index（corpus_kind=discussion, attribution=nascent）
  → retrieve 时可与 linked_cards 子图联合召回
  → 若讨论中形成可维护主张 → capture / digest → write --batch 升格为 Card
  → discussion 保留，status 可标 superseded，linked_cards 补全
```

　　**归因纪律**：Context Package 中来自 discussion 的块必须标 `attribution: nascent`，与 `origin: user` 的卡片、`origin: document` 的卡片区分。

### 4.3 与 Journal 的区别

| | Journal | discussion |
|--|---------|------------|
| 粒度 | 单行操作事实 | 完整论述与证据 |
| 目的 | 审计、反思输入 | 检索、补充细节 |
| RAG | 可选、低权 | 默认入 RAG、中权 |

---

## 5. 结构轨：图索引与检索

### 5.1 模块（`nexogenesis/graph/`）

| 模块 | 职责 |
|------|------|
| `build.py` | 从 `Store` 抽边：relation、wikilink、domain、involves |
| `store.py` | 读写 `.nexogenesis/graph/` |
| `traverse.py` | BFS/DFS，关系类型与 hop 策略 |
| `retrieve.py` | 种子 → 扩展 → 排序 → 结构区 Context |
| `analyze.py` | orphan、conflict 缺口、桥接点；输出 metrics + **结构变更提案** |
| `export.py` | GraphML（P2） |

### 5.2 边与节点

与 v0.11 设计一致：`Store.cards` 为节点；边来自 `relations`、`[[wikilink]]`、`domains`、`conflicts-involves`。

### 5.3 检索策略（G1，默认）

1. **种子**：query 分词 + domain 匹配 + `--seed` + digest 时 Buffer 的 `proposed_domains` / 加粗词  
2. **扩展**：hop≤2，第二跳过滤 relation 类型；遇 conflict 拉 involves 各方  
3. **预算**：`max_nodes` + `max_chars`；结构区优先卡片摘要与关系路径  
4. **空图**：返回 `status: empty-graph`，不报错  

### 5.4 图分析 → 结构提案

　　`analyze` 除报告外，输出 `structure_ops.json`（**非自动执行**）：

```json
{
  "ops": [
    {
      "op": "suggest_conflict_card",
      "reason": "A conflicts-with B 无 covering conflict",
      "cards": ["a-id", "b-id"]
    }
  ]
}
```

　　由 construct `--lens distinguish` 或 Agent 转为 `write --batch` 候选。

### 5.5 阶段门控

| 阶段 | 内容 | 进入条件 |
|------|------|----------|
| G0 | rebuild + stats | 立即 |
| G1 | retrieve + analyze | 卡片 ≥20 或 digest 深读漏召回 |
| G2 | 图种子 + 向量 RAG 融合 | 黄金集证明 G1+FTS 不够 |
| G3 | 社区摘要 | 全局主题问法频繁且 G2 不够 |

---

## 6. 质料轨：RAG 索引与检索

### 6.1 原则

- **语料真身仍在 markdown**；`.nexogenesis/rag/` 仅索引。  
- **先 FTS/BM25，后向量**：P1 默认稀疏检索即可覆盖大量「精确短语 / 章节」需求。  
- 向量层可选，由环境变量配置 embedding 提供方；无配置时仅 FTS。

### 6.2 目录布局

```text
.nexogenesis/rag/
  manifest.jsonl      # 每 chunk 一行：chunk_id, path, kind, meta, char_span
  fts/                  # SQLite FTS5 或等效
  embeddings/           # 可选；chunk_id → vector
  last_build.json       # 源文件 mtime 指纹，增量索引
```

### 6.3 索引命令

```bash
python -m nexogenesis rag index [--full] [--kinds archive,buffer,discussion,outbox]
python -m nexogenesis rag stats
```

**触发时机**：

- `compile --apply` 成功后：索引新 buffer + 新 archive  
- 用户保存 `04-OutBox/discussions/*.md` 后：手动或 hook `rag index --kinds discussion`  
- `write --batch` 成功后：更新 `card_excerpt` 与 manifest 中 linked 语料  

### 6.4 检索命令

```bash
python -m nexogenesis rag search --query "..." [--kinds discussion,archive] [--top 12]
```

返回每条：**chunk 文本节选 + 完整锚点**（路径、章节、页码、linked_cards）。

### 6.5 与图的联动（锚点扩展）

　　当 graph retrieve 命中卡片 `C` 时，RAG 自动加查：

- `linked_cards` 含 `C` 的 discussion  
- `card.sources` 指向的 archive 路径  
- `buffer` 中 `source` 与 C 的 sources 重叠的片段  

　　此为 **结构→质料** 单向拉取，避免 RAG 噪声反向污染图遍历种子。

---

## 7. 统一检索：Hybrid Context Package

### 7.1 入口

```bash
python -m nexogenesis retrieve --query "..." \
  [--mode talk|digest|construct|answer] \
  [--budget-chars 16000] \
  [--graph-hops 2] \
  [--rag-top 8]
```

　　内部：`graph.retrieve()` + `rag.search()` + 合并去重 + 归因标注。

### 7.2 输出 schema（摘要）

```yaml
query: "..."
mode: talk
status: ok   # ok | empty-graph | no-rag-hits

structure:
  seeds: [教学]
  nodes:
    - id: 教学反馈应指出可操作差距
      type: claim
      hop: 1
      via: "domain:教学"
      excerpt: "…"
  edges:
    - { from: 教学, to: 教学反馈应指出可操作差距, type: applies-to }

material:
  - chunk_id: sha256:...
    kind: discussion
    attribution: nascent
    anchor: "04-OutBox/discussions/2026-07-27-反馈差距研讨.md#第二节"
    excerpt: "…"
    linked_cards: [教学反馈应指出可操作差距]
  - chunk_id: ...
    kind: archive
    attribution: document
    anchor: "03-Archive/paper.pdf §3.2"

blind_spots:
  - "未启用向量；隐喻问法可能漏召回"
budget: { chars: 14200, structure_nodes: 8, rag_chunks: 5 }
```

### 7.3 各 mode 的默认权重

| mode | 结构区权重 | 质料区权重 | 说明 |
|------|------------|------------|------|
| `talk` / `answer` | 高 | 中 | 先立结构，用 RAG 补细节与引文 |
| `digest` | 高 | 高（buffer 优先） | 同波 buffer 全文 + 相关 archive |
| `construct` | 极高 | 低 | 以图分析与结构信号为主 |
| `judge`（升级） | 高 | 中 | 强化 conflict 子图 + 对立证据块 |

---

## 8. 与现有流水线的衔接

```text
00-Inbox → compile → 05-Buffer ──rag index──┐
                ↓                           │
           03-Archive ──rag index────────────┤
                ↓                           │
           digest ──retrieve(mode=digest)───┼──→ LLM → batch → Cards（图）
                ↓                           │
           construct ← graph analyze ───────┘
                ↓
           talk/answer ← retrieve(mode=talk)
                ↓
           讨论整理 → 04-OutBox/discussions ──rag index──→ 新生证据
                ↓
           值得长期维护 → capture → batch → Cards
```

| 现有模块 | 检索升级后 |
|----------|------------|
| `context_pack.select_deep_cards` | 调用 `graph.retrieve`（digest 模式） |
| `card_catalog` | 保留；结构区仍可提供全库目录一行摘要 |
| `structure_signals` | 与 `graph.analyze` 合并为单一分析后端 |
| `index` 命令 | 保留人类视图；与 `graph rebuild` 并行 |

---

## 9. Harness CLI 汇总（规划）

```bash
# 图
python -m nexogenesis graph rebuild
python -m nexogenesis graph stats
python -m nexogenesis graph analyze
python -m nexogenesis graph retrieve --query "..." --hops 2

# RAG
python -m nexogenesis rag index [--full]
python -m nexogenesis rag search --query "..."

# 统一
python -m nexogenesis retrieve --query "..." --mode talk
```

　　`write --batch` 成功后的顺序建议：`validate` → `index` → `graph rebuild` → `rag index`（增量）。

---

## 10. 实施路线图

| 阶段 | 交付 | 依赖 | 空库可测 |
|------|------|------|----------|
| **R0** | `graph rebuild` + `stats` + write 后 hook | Store | ✅ |
| **R1** | `graph retrieve` + 接 digest 深读 | R0 | ✅ |
| **R2** | `rag index/search`（FTS）；语料 archive+buffer | markdown 路径 | ✅ |
| **R3** | `retrieve` 统一命令；Context Package schema | R1+R2 | ✅ |
| **R4** | `discussions/` 约定 + discussion 入 RAG | R2 | ✅ |
| **R5** | `graph analyze` + structure_ops → construct | R0 | ✅ 已实现 |
| **R6** | 向量层 + RRF 融合 | R3 + 黄金集 | **延后**（暂无 embedding） |
| **R7** | GraphML / 可视化 | R0 | ✅ `graph export` |

　　**推荐并行**：R0–R1 与 R2–R4（图与 RAG 可不同 PR）；R3 为汇合点。

---

## 11. 评测与进入条件

| 指标 | 用途 |
|------|------|
| 结构 Recall@k | graph retrieve 是否带回应用卡片 |
| 质料 Recall@k | RAG 是否带回应用 anchor |
| 归因错误率 | nascent/document/user 是否被 LLM 混用 |
| 结构效用 | retrieve 后写入是否减少重复卡、冲突升格是否增加 |
| 用户纠正率 | talk/answer 后用户更正比例 |

　　更新 `AGENTS.md` §十：图检索进入条件改为「R1 完成且卡片≥20」；向量进入条件为「R3+R6 黄金集」。

---

## 12. 禁止与必须

### 禁止

- ❌ 将 RAG chunk 直接写成 Card 或 `relations`（须 batch）  
- ❌ 把 discussion 默认标为 `origin: user` 的成熟主张  
- ❌ RAG 索引作为唯一事实源（删 markdown 后不得保留语义）  
- ❌ 未归档 Inbox 全文入 RAG（与 compile 职责重叠）

### 必须

- ✅ 每个 RAG 命中带可点击/可打开的文件锚点  
- ✅ Context Package 区分 structure / material 与 attribution  
- ✅ discussion 入 RAG 时标 `nascent`  
- ✅ 索引可全量重建；`doctor` 可检测索引陈旧  

---

## 13. 撤回方式

| 机制 | 撤回 |
|------|------|
| graph retrieve | `--no-graph` 回退 catalog + select_deep_cards |
| RAG | 删除 `.nexogenesis/rag/`；仅用图与卡片正文 |
| 向量 | 删除 `embeddings/`；保留 FTS |
| discussion 语料 | 移出 `discussions/` 或标 `status: archived` 后重跑 index |

---

## 14. 与终局目标的对齐

| 终局能力 | 本设计中的落点 |
|----------|----------------|
| 知识结构可演进 | 图检索 + analyze → structure_ops → batch |
| 思维体带立场对话 | retrieve(mode=talk) 结构区 + 归因 |
| 细节不丢 | archive / buffer / RAG |
| 讨论产生新证据 | discussions + nascent + 可选升格 |
| 底座主权 | 一切索引可删；语料仍在 markdown |

---

> 修订记录：2026-07-27 首版，确立双轨检索与新生证据约定。
