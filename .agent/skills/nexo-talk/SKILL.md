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
