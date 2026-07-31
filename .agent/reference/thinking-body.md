# 思维体：短期记忆 · 注意力组装 · 强信号（设计草案）

> 状态：S0–S4 已实现（2026-07-28）  
> 活契约：`AGENTS.md` §4.8；权重模板：`schemes/default/attention.yaml`  
> 相关：`docs/2026-07-27-retrieval-graph-rag-design.md`（双轨检索）

---

## 1. 目标体验

　　用户默认与思维体**流畅对话**（分析、思考、联结）；仅在「沉淀为结构」时进入明显仪式。写入知识体永远经用户确认。系统在强信号时主动轻问，不把内部相位当成用户菜单。

　　认知隐喻（产品层）：

| 层 | 含义 | 本项目落点 |
|----|------|------------|
| 工具书 | 手边可翻的证据与细节 | RAG / 搜索（archive、buffer、discussion…） |
| 长期记忆 | 已承诺的知识结构 | 卡片图（`01-Cards` + relations + 索引视图） |
| 短期记忆 | 跨会话连贯的工作记忆 | 会话档案（非 Card，见 §3） |
| 注意力组装 | 每轮高关联、有限体积的 Working Set | 增强版 Context Package（见 §4–§5） |

　　**强信号**（§6）与注意力**不是同一层**：注意力每轮都工作；强信号只在少数时候「敲门」问要不要捕获 / 加深 / 摄入。

---

## 2. 已拍板纪律（交互）

1. **强信号时主动提问**（有可解释触发 + 冷却）。  
2. **对话捕获永远用户确认**（禁止对话路径 `approved_by: agent` 写卡）。  
3. **分析默认留在对话**（不默认落 OutBox）。  
4. **提及 Inbox / 未消化材料时可温和建议 compile**（不自动开流水线）。

---

## 3. 短期记忆（STM）

### 3.1 容量模型

　　**不按自然日过期**，按**会话卷**滚动：

- 保留最近约 **10 次会话**的档案 + **当前会话**正在写入的槽；  
- 「一次会话」= 一次连贯对话窗口（实现上可等于一个 `session_id`，由 Agent/Harness 在对话开始时分配）；  
- 超出 10 次的旧档案：压缩为极短「化石摘要」一条，或直接丢弃（配置项，默认丢弃细节、可选留一行标题）。

### 3.2 构成

```text
短期记忆 = 跨会话档案（≤10 卷） ∪ 当前会话槽（热）
```

| 槽 | 内容 | 备注 |
|----|------|------|
| `focus` | 当前问题 / 用户要的结果 | 注意力主锚 |
| `claims_user` / `claims_system` | 本会话主张（分归因） | 捕获原料 |
| `tensions` | 未决对立与犹豫 | 联结与 conflict 苗床 |
| `cited_cards` | 已引用 card id | 避免重复；enrich 优先 |
| `rag_footprints` | 翻过的工具书 anchor | 可追溯，不升格 |
| `user_directives` | 「先别记」等 | 关闭主动捕获等 |
| `bridge_hints` | 本会话意外连上的旧卡 | 供「惊艳联结」复用 |

### 3.3 存储与主权

- **路径建议**：`.nexogenesis/memory/stm/`（可删；**不是**语义事实之源）。  
  - `index.yaml`：卷列表、当前 `session_id`、容量策略  
  - `session-<id>.yaml`：单卷槽内容  
- **禁止**：STM 内容不经捕获闸门直接变成 Card / relations。  
- **可读性**：YAML 优先（机器组装）；若需人工翻阅，可另导出 markdown 视图，仍属可重建物。

### 3.4 更新

- 每轮或每 N 轮：由模型改写当前卷槽（Harness 可只做合并与截断）。  
- 会话结束：封存当前卷；若卷数 > 10，丢掉最旧一卷（或按配置折叠）。  
- 与双轨检索：`cited_cards`、`focus` 代币作为下一轮 graph/RAG 的种子加成。

---

## 4. 注意力组装（Working Set）

### 4.1 目标

　　每轮构造体积有限、**关联密度高**的上下文，使模型更易产生「接到意想不到但合理的旧卡」的联结感；同时**不放弃**把对立面摆上台面。

### 4.2 组装顺序（逻辑管道）

1. 当前话语（本轮 + 近几轮要点）  
2. 短期记忆槽（焦点、张力、主张、已引用、禁令）  
3. 长期记忆子图（graph；种子 = 焦点词 + cited + STM bridge_hints）  
4. 工具书片段（RAG；按需，discussion 标 `nascent`）  
5. 硬约束条（极短：归因纪律、写入纪律、用户禁令）

### 4.3 双偏重：扩展联结 × 冲突拉扯

　　用户倾向：**更偏前者，但不放弃后者**。实现上拆成两个**预算账户**，而不是单一排序分。

| 账户 | 目标 | 选人策略（示意） |
|------|------|------------------|
| **扩展（expansion）** | 惊艳但合理的旧卡 | 与焦点同域/同词，但**尚未**在 `cited_cards`；优先弱连接、桥接点、二跳邻居；降低「只会重复本会话已引用卡」 |
| **冲突（conflict）** | 对立面在场 | 保留**保底名额**：`conflicts-with` 邻居、conflict 卡、`tensions` 槽；即使相似度略低也占一席 |

**如何同时实现（推荐）**：

```text
Working Set 卡片位 = expansion_slots + conflict_slots + (可选) core_slots
```

- `core_slots`：种子卡与 STM 已引用（保底连贯）  
- `expansion_slots`：按「相关性 × 新奇度」排序填满（新奇度 = 未引用、弱连接、桥接）  
- `conflict_slots`：**先扣预算再填扩展**，避免扩展抢光窗口后冲突永远进不来  

**评分示意**（可在 YAML 调权重）：

```text
expansion_score = w_rel * relevance + w_novel * novelty - w_dup * already_cited
conflict_score  = w_rel * relevance + w_tension * tension_match + w_edge * has_conflicts_with
```

　　「顿悟」不可保证；可观测代理指标：扩展卡在后续对话中被用户正向引用的比例、冲突席是否经常被用户认为「有用而非抬杠」。

### 4.4 与现有 `retrieve` 的关系

　　现行 Context Package = 结构区 + 质料区。本草案 = **STM 注入 + 双账户选卡 + 权重配置**。实现时可演进为 `retrieve --mode talk` 的内部策略，或独立 `assemble` 步骤；索引仍可删可重建，STM 除外（STM 丢了只影响连贯，不影响知识主权）。

---

## 5. 权重如何控制：YAML 方案（及备选）

### 5.1 推荐：YAML 配置 + 模式预设

　　**主方案**：用一份人类可改的 YAML 控制注意力与强信号阈值。理由：与本项目「文件即契约」一致、无需 UI、Agent 与用户都能 diff。

```text
schemes/default/attention.yaml     # 方案默认（随 scheme）
.nexogenesis/attention.yaml        # 项目覆盖（可选；不进语义库）
```

　　合并规则：项目文件覆盖 scheme 默认；未知键忽略并 warning。

　　**预设（profile）**：`talk` / `answer` / `judge` / `digest` 指向不同权重块，避免为每种对话手改几十个数。日常只改 `active_profile` 或改某一 profile 内的数。

### 5.2 为何不只用环境变量 / 代码常量

| 方式 | 优点 | 缺点 |
|------|------|------|
| YAML（推荐） | 可调、可版本管理、可读 | 需校验范围 |
| 仅代码常量 | 实现快 | 调参要改代码 |
| 纯自然语言「这次偏冲突」 | 灵活 | 不可复现、难测 |
| 学习式自动调权 | 长期可做 | P 阶段证据不足，易不透明 |

　　**更好的组合**：YAML 管默认与可复现实验；对话里用户说「这次多拉点冲突」→ **只影响当前会话覆盖层**（写在 STM `user_directives` 或 session overlay），不改永久 YAML。

### 5.3 配置草案（示意）

完整模板见仓库：`schemes/default/attention.yaml`。

要点字段：

- `stm.max_sessions`：默认 `10`  
- `budget.chars` / `budget.card_slots` / `budget.rag_chunks`  
- `slots.core` / `slots.expansion` / `slots.conflict`  
- `weights.expansion.*` / `weights.conflict.*`  
- `rag.enabled` / `rag.max_chunks` / 各 mode 的 kinds  
- `strong_signals.*`：阈值、冷却、开关  

---

## 6. 强信号（门铃层）

　　与注意力共用「本轮焦点」，但独立阈值。

| 信号 | 提问类型 | 备注 |
|------|----------|------|
| 用户说「记一下」等 | 捕获 | 最高优先 |
| 可复用新主张且库中无同题 | 捕获轻问 | 须可解释 |
| 清晰对立且可指向两边 | 冲突草稿？ | 可选 |
| 同一问题在 STM 反复出现 | 进问题清单？ | |
| 高风险议题 | 加深判断？ | 分析仍默认留对话 |
| 提及 Inbox / 未消化文 | 要不要 compile？ | 温和建议 |

　　纪律：同会话捕获主动问 ≤ 配置上限；`user_directives` 可关闭；**永不**因强信号自动 write 卡片。

---

## 7. 数据流（草案）

```text
用户发言
  → 读 attention.yaml（+ 会话覆盖）
  → 读/更新 STM 当前卷
  → graph：core + expansion 账户 + conflict 账户
  → rag：工具书（按预算）
  → 组装 Working Set → LLM 回复
  → 更新 STM 槽
  → 强信号策略 → 可选一句轻问
  → 若用户确认捕获 → 自然语言候选 → 用户批改 → write --batch
```

---

## 8. 非目标（本草案）

- 不实现 Transformer 内部 attention；不引入向量 EBD（仍延后）。  
- 不把 STM 升格为 Card；不自动改 `AGENTS.md`。  
- 不做学习式自动调权。  
- 不替代 compile / digest / construct 记忆体流水线。

---

## 9. 建议实现顺序（供后续开工，非本次）

| 步 | 交付 | 验收 |
|----|------|------|
| S0 | `attention.yaml` 模板 + 加载/合并/校验 | ✅ `attention show\|validate` |
| S1 | STM 卷存储与 10 会话滚动 | ✅ `memory start\|update\|end` |
| S2 | Working Set 双账户组装（接 retrieve） | ✅ `retrieve --mode talk` 含 accounts |
| S3 | 强信号规则 + 冷却 | ✅ `signal --text` |
| S4 | 会话级覆盖（「这次偏冲突」） | ✅ `memory override` |

---

## 10. 开放问题（已部分收敛）

| 问题 | 现状 |
|------|------|
| 权重控制方式 | **采用 YAML + profile**；会话覆盖作临时偏置 |
| STM 寿命 | **约 10 次会话**，非按天 |
| 扩展 vs 冲突 | **双预算账户**；默认扩展席更多，冲突席保底 |
| 化石摘要是否保留第 11+ 卷标题 | 默认丢弃；YAML 可开 |

---

## 11. 与 `AGENTS.md` 的关系

　　本草案稳定后，建议在 `AGENTS.md` 增一短节「思维体：对话面 / 闸门面 / STM·注意力」，**指向本文与 `attention.yaml`**，避免再把 `/talk` `/judge` 写成用户必选菜单。修订 `AGENTS.md` 前须用户确认（现行契约）。
