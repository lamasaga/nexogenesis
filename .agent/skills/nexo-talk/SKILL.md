---
name: nexo-talk
description: >-
  Nexogenesis thinking-body default dialogue: retrieve + STM, attribute
  user/document/system/nascent, keep analysis in chat, never auto-write cards.
  Use for normal conversation, 聊聊, 分析一下, 想想, /talk, or when no explicit
  capture/digest/construct intent.
---

# nexo-talk（思维体 · 思考）

## 触发条件

- 日常对话、分析、思考；
- 没有明确的捕获/消化/建构意图。

## 步骤

1. 若无会话：`python -m nexogenesis memory start --title "…"`
   - 或 `memory status` 复用当前卷。
2. `python -m nexogenesis retrieve --query "<当前问题>" --mode talk --root .`
3. 读取 Context Package：
   - 区分 **structure** vs **material**；
   - 归因 **user / document / system / nascent**；
   - 读取 `02-Profile/领域理念.md` 与 `02-Profile/领域思维模型.md` 作为领域透镜。
4. 回答：直接、有据；仅当存在相关 `theory_status: active` 时声明「从 X 视角」。
5. 可选：`memory update` 写入 focus / tensions / cited_cards。
6. 强信号时可跑 `signal --text "…"`；若建议捕获 → 转 `nexo-emerge`，先轻问用户。

## 纪律

- 分析默认留在对话；写入知识体永远另走 `nexo-emerge`。
- 禁止对话路径直接改 `01-Cards/` 或以 `approved_by: agent` 写卡。
- 不扫全库卡片；靠 retrieve + 索引视图。
- 「先别记」→ 记入 STM `user_directives`，本会话关闭主动捕获。
- Inbox 有未处理材料时可温和建议 `nexo-compile`，不自动开流水线。

## 必读文档

- `AGENTS.md` §4.1、§4.4（思维体底线）
- `docs/2026-07-28-thinking-body-attention-design.md`
- `02-Profile/领域理念.md`
- `02-Profile/领域思维模型.md`
