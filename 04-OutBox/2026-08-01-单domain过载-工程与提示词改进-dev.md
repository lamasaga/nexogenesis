# 单 Domain 过载：工程设计与提示词优化观点

> 日期：2026-08-01  
> 性质：设计观点与改进建议（非 Card；默认不作已定结论）  
> 背景：曼昆第01–20章 compile→digest 后，库内仅 1 张 domain「市场效率与政策干预」，实例卡几乎全部挂靠；domain `relations` 持续 >12 warning，正文变成全书进度条。  
> 关联：`AGENTS.md` 双层结构；`nexo-digest` / `digest.txt`；`04-OutBox/2026-08-01-digest清空Buffer问题与防呆设计.md`

---

## 1. 核心观点（一句话）

　　单 domain 过载不是「教材太大」的必然结果，而是 **bootstrap 局部命名 + 挂靠契约 + 编排提示把「禁止幽灵」收成「禁止第二张」+ enrich/检索自强化 + construct 缺席** 的路径依赖。工程上缺的是 **领域分裂的闸门与预算**；提示词上缺的是 **何时新建 sibling domain 的可判定标准**。

---

## 2. 分层诊断

### 2.1 工程 / Harness 层

| 机制 | 实际效果 | 问题 |
|---|---|---|
| 空库须先 domain | 保证有骨架入口 | 首波用 **局部章节主题** 命名，却成为 **全局唯一挂靠点** |
| 实例 `domains` 必须引用已有/本批 domain | 防幽灵链接 | 目录里只有 1 张时，等价于强制单点挂靠 |
| digest 主职 enrich、结构重组留给 construct | 职责清晰 | construct 未跑 → 分裂债务无限期推迟 |
| 深读卡含 domain | 每波看见领域入口 | 唯一 domain 每波被再读、再 enrich、再加边 |
| `relations`/`sources` 仅 warning | 不阻断写入 | 枢纽膨胀无硬停机条件 |
| 无「domain 覆盖度 / 主题漂移」信号 | — | 系统不知道该不该拆 |

　　结论：Harness 很好完成了 **「至少有一张 domain」**，几乎没完成 **「domain 粒度与语料主题对齐」**。前者是 bootstrap 正确性；后者是长期可导航性。

### 2.2 提示词 / Agent 编排层

| 提示习惯 | 意图 | 异化结果 |
|---|---|---|
| `domains 必须含「市场效率与政策干预」` | 防漏写 / 防幽灵 | 禁止探索第二 domain；新建额度全给 model/conflict |
| 「enrich 优先；新建 ≤N」 | 防逐片转卡 | domain 永远「够相关」→ 只 enrich 不分裂 |
| 「enrich domain：更新肖像/张力」 | 滋养骨架 | 把章进度、政策菜单、劳动地图一并灌进同一张 |
| 偶发「必要时可新建 domain」 | 留口子 | 无判定标准、无预算、无示例 → 实际零触发 |
| 决策树「同主题 → enrich」 | 聚合涌现 | **同主题粒度未定义**：全书微观都算同主题 |

　　结论：提示词把 **契约的下限（必须有合法 domains）** 写成了 **操作的上限（只能用这一张）**。这是经典的「安全提示过约束」。

### 2.3 语义 / 本体层（材料事实）

　　曼昆教学顺序 ≠ 单一社科领域。效率—政策干预、贸易与比较优势、产业组织、要素与歧视，至少是 **可并行的 domain 簇**。用一张政策叙事的 domain 吞企业理论与劳动分配，本体上必然过载。

---

## 3. 设计原则（建议采纳）

1. **Domain 是导航单元，不是全书垃圾桶**  
　　一张 domain 应能用 3–5 个核心问题说清边界；装不下就分裂，而不是继续 enrich「内在张力」。

2. **「禁止幽灵」≠「禁止第二张」**  
　　挂靠合法性与领域个数正交：允许多 domain；禁止的是指向不存在的 id。

3. **主题漂移是一等公民信号**  
　　当 Buffer 簇的核心问题已无法用现有 domain 的「核心问题」列表覆盖，应触发 **新建 sibling domain**（计入结构单元预算），而不是强制挂旧卡。

4. **Digest 可「立」第二 domain；Construct 「理」挂靠与边**  
　　不要把「能不能有第二张」全部推给 construct；construct 负责合并过细、重挂 `domains`、压缩 hub 边。

5. **Deep-read 与挂靠解耦**  
　　深读应按本波 Buffer 主题检索相关 domain（可多张），而不是永远置顶唯一 hub。

---

## 4. 改进建议

### 4.1 提示词优化（见效快，P0–P1）

**P0｜改写硬规则文案（立即）**

　　删除或改写：

```text
❌ domains 必须含「市场效率与政策干预」
```

　　改为：

```text
✅ domains 必须引用「本批新建或目录已有」的合法 domain id（可多值）。
✅ 默认优先挂「与本波核心问题最贴」的 domain；勿为省事一律挂同一张。
✅ 若本波质料的核心问题无法被现有任一 domain 的「核心问题/边界」覆盖 → 允许新建 1 张 sibling domain（计入本波结构单元预算，通常 ≤1）。
✅ 禁止：用 enrich 旧 domain「内在张力」代替本该独立的领域入口。
```

**P0｜在 `digest.txt` 增加「Domain 分裂判定」短段**

　　建议判定（须可操作、少哲学）：

1. 现有 domain 的核心问题列表中，**没有任何一条**能以「是/否」覆盖本波主问题；或  
2. 本波主机制所属教科书「篇」（如企业理论 vs 要素市场 vs 福利政策）与现有 domain 标题/肖像 **明显错位**；或  
3. 若强制挂靠，只能写出空心「原文未提及：本领域边界」式边界段。  

　　满足其一 → **新建 domain**；否则挂最贴的一张，并可 `applies-to` 弱连到相邻 domain（勿堆 15 条 hub 边）。

**P1｜结构单元预算含 domain**

　　把「新建 Card ≤N」改成「结构单元 ≤K」：

- 新建/实质升格 1 张 domain = 1 单元  
- 一组 conflict bundle（conflict + 两造）= 1 单元  
- 1 张独立 model = 1 单元  

　　并写明：**主题漂移波次应优先花 1 单元在 domain，而不是第 4 张边缘 claim。**

**P1｜Enrich domain 的「准许改什么」**

```text
允许：核心问题微调、边界澄清、与本波直接相关的 1 条内在张力、压缩 sources。
禁止：把整章 Nutshell/政策菜单/进度表写入 domain；禁止本波仅为挂靠新增 >2 条 applies-to。
实例细节进 instance；domain 只保留领域级出处（如「曼昆微观·福利与政策篇」）。
```

**P2｜子代理交付清单加一项**

```text
[ ] 本波挂靠的 domain id 列表 + 一句「为何不新建/为何新建」
```

　　迫使显式决策，避免默认锁死。

---

### 4.2 工程 / Harness 优化（中期，P1–P2）

**P1｜Domain 健康度信号（diagnose / digest --plan）**

　　在 `digest --plan` 或 `construct` diagnose 输出：

- 每张 domain 的挂靠实例数、`relations` 数、body 字符数  
- 告警阈值建议：挂靠 >25 或 relations >12 或 body >3k → `domain_overloaded`  
- 若本波 Buffer 的 RAG/标题关键词与现有 domain 肖像重叠度低 → `theme_drift_suggest_new_domain`

**P1｜Deep-cards 按主题选 domain**

　　不要固定「唯一 domain + 随机实例」。改为：由本波 Buffer 检索 top-k domain（k≥1）；若库内仅 1 张且 drift 高，在 prompt 顶部插入 **bootstrap-sibling** 提醒块。

**P2｜写入闸门（可选 strict）**

- `--strict-hub`：domain `relations` >12 且本波仍向该 domain 追加 relation → hard fail，要求改挂或新建  
- enrich domain 时若 `sources` 含超过 M 条 Buffer 路径 → warning「请压缩为篇级出处」

**P2｜Construct lens：`split-domain` / `rehome-domains`**

　　专用透镜：

1. 提议 2–4 个 sibling domain 标题与核心问题  
2. 批量改实例 `domains` 字段（经 write --batch）  
3. 压缩旧 hub 的 applies-to，只留跨领域桥接边  

　　Digest 负责「该立时立」；Construct 负责「立歪了理顺」。

**P3｜Bootstrap 命名策略**

　　空库首域避免用过窄政策标签。可选：

- 用更中性的伞名（如「微观市场与激励」）+ 后续强制分裂；或  
- 首波若多主题 tension 混抽，**允许同批建 2 张 domain**（仍先骨架后实例）  

　　并在 journal 记录：`bootstrap_domain_provisional: true`，提醒早期 construct。

---

### 4.3 与「回答质量 / vs RAG」的衔接

　　Domain 过载会把知识体推回「长摘要」，削弱相对切片 RAG 的结构优势。改进目标应可验收为：

| 验收项 | 目标态 |
|---|---|
| domain 张数 | 随教材篇级主题 ≥2–4（微观导论/福利政策/产业组织/要素与分配等，按实际质料） |
| 单 domain 挂靠 | 建议 <25 张实例，或可解释的枢纽例外 |
| 回答路由 | 结构题先选对 domain 再下钻；事实题仍走 RAG |
| Prompt | 不再出现「必须含某一固定 domain id」字样 |

---

## 5. 建议落地顺序

1. **立刻（提示词）**：改掉「必须含×× domain」；加入分裂判定 + enrich domain 准许表；子代理交付要求说明挂靠理由。  
2. **下一轮 digest 前（Harness 轻改）**：`--plan` 输出 domain 健康度与 theme_drift 提示；深读多 domain。  
3. **本库现状（Construct）**：开一轮 `split-domain`，把现有「市场效率与政策干预」拆成至少「福利与政策干预 / 企业与市场结构 / 要素与收入」三类（名称可再议），并重挂实例。  
4. **其后**：strict-hub 与 bootstrap 命名策略写入活契约（`.agent/reference/`），避免路径依赖重演。

---

## 6. 反模式清单（提示词与编排忌写）

- 「所有卡 domains 填同一个 id」  
- 「每波都要 enrich domain」  
- 「新建 domain 算浪费新建名额」  
- 「construct 以后再说，digest 先全部挂上」  
- 「书名/课程名直接当唯一 domain」

---

## 7. 结语

　　工程上，系统已经会 **造入口**；还不会 **管粒度**。提示词上，系统已经会 **防幽灵**；还不会 **促分裂**。  
　　把「domain 健康度」做成可观测信号，把「主题漂移 → sibling domain」写成可判定提示，再让 construct 承担重挂——单 domain 过载才能从「复盘共识」变成「默认不会再发生」。
