---
name: nexo-talk
description: |
  Nexogenesis 思维体默认对话：检索 + 短期记忆，区分 user/document/system/nascent 归因，
  把分析留在对话中，禁止自动写卡。当用户闲聊、要求分析/思考、说「聊聊」「想想」，
  或没有明确捕获/消化/建构意图时触发。
compatibility: Nexogenesis 项目，已初始化 .agent/reference/ 与 02-Profile/
---

# Grounding（按顺序必读）

1. `.agent/reference/constraint-layers.md` — 约束分层：宪法 / skill / reference / prompt。
2. `.agent/reference/thinking-body.md` — 思维体注意力设计。
3. `.agent/reference/retrieval-design.md` — 双轨检索与 Context Package 结构。
4. `02-Profile/领域理念.md` — 领域级立场与价值取向。
5. `02-Profile/领域思维范式.md` — 领域级推理模式与反模式。

# Workflows

> 完整 CLI 参数见 [`.agent/reference/harness-cli.md`](.agent/reference/harness-cli.md)；以下只列出本 skill 的典型调用顺序。

1. 若无活跃 memory session：
   ```bash
   python -m nexogenesis memory start --title "<当前主题>" --root .
   ```
   或先 `python -m nexogenesis memory status --root .` 复用当前卷。
2. 根据用户问题执行双轨检索：
   ```bash
   python -m nexogenesis retrieve --query "<当前问题>" --mode talk --root .
   ```
3. 读取 Context Package：
   - 区分 `structure`（图子图）与 `material`（RAG 质料）；
   - 区分归因：`user` / `document` / `system` / `nascent`；
   - 把 `02-Profile/` 中的理念与思维模型作为透镜。
4. 回答用户：直接、有据；仅当存在 `theory_status: active` 的卡片时，方可声明「从 X 视角」。
5. 可选：若对话中出现值得追踪的焦点/张力/引用，追加到短期记忆：
   ```bash
   python -m nexogenesis memory update --focus "…" --cite "<card-id>" --tension "…" --root .
   ```
6. 强信号时（用户明显在表达一个值得沉淀的主张）可跑：
   ```bash
   python -m nexogenesis signal --text "<摘要>" --root .
   ```
   若 signal 建议捕获 → 轻问用户「是否记一下？」→ 用户同意则转 `nexo-emerge`。

# 抽象问题与深思（宏观分野 / 根源类提问）

- **先钉用语**：用户用词抽象时，先在回答内界定其在本库的含义（可能多义），再检索。
- **检索策略**：先机制词、后学派标签。第一枪看 seeds；噪声大（跑题枢纽混入）则用卡 id/术语打第二枪，不要只把同一句加长。
- **强制种子**：已知关键卡时用 `python -m nexogenesis retrieve --seed "<card-id>"`（可多值）钉住种子，避免宽词噪声稀释注意力。
- **深思摘录**：默认单卡摘录 800 字；深思/涌现场景用 `--excerpt-chars 2000` 加大，减少旁路扫全库。
- 仍不足再定向读 5–15 张枢纽卡正文；回答分清 `document`（库内）与 `system`（综合）。

# 涌现姿态

- 不要求「全新理论」：把已有卡做相位重组，提出 3–5 个**可命名、可检验**的假说；每条至少挂一张卡锚，并明确标注 `system`（未写卡）。
- 结束时按 Workflows 第 6 步轻问是否捕获；用户同意才转 `nexo-emerge`。

# 表达纪律（面向用户的分析讨论）

- 禁止「术语拼接摘要」作为主交付：**先人话，后专名**；专名出现时必须带一句作用（这张卡提醒我们问的是哪一个问题）。
- 复杂主张/外部言论评析默认五段骨架（可裁剪，不可颠倒成先堆术语再补故事）：材料边界 → 拆题 → 逐步推演（若接受 → 推出什么 → 还缺哪一问）→ 并置冲突（人话写清，再给表）→ 定位式评判。
- 表格是附录不是正文；正文须已能独立读懂。
- 发出前自检：删去所有卡片 id 与英文缩写后，用户是否仍能复述结论依据？不能则重写。

# Invariants

- 分析默认留在对话；写入知识体必须另走 `nexo-emerge`。
- 对话路径禁止直接修改 `01-Cards/` 或以 `approved_by: agent` 写卡。
- 未标注 perspective 时，文档观点标 `document`，用户立场标 `user`，系统推断标 `system`，讨论质料标 `nascent`。
- 不扫全库卡片；依赖 `retrieve` + 索引视图。
- 用户说「先别记」→ 记入 STM `user_directives`，本会话关闭主动捕获。

# Anti-patterns

- 把对话中的临时分析自动写成 Card。
- 把 RAG 命中当成成熟主张直接复述为用户立场。
- 在不存在 `theory_status: active` 卡片时声称「从理论 X 视角」。
- 不读 Context Package 就空泛回答。
- 把卡名对照表当分析交付；用无动词的术语串代替推理过程。
