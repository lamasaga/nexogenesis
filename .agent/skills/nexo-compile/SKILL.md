---
name: nexo-compile
description: |
  Nexogenesis 编译：把 00-Inbox/ 原始文档按体裁开窗切块，产出 05-Buffer/ 质料。
  当用户说「编译」「/compile」「处理 Inbox」或 00-Inbox/ 有新文档时触发。
compatibility: Nexogenesis 项目，已初始化 .agent/reference/ 与 schemes/default/prompts/
---

# Grounding（按顺序必读）

1. `.agent/reference/constraint-layers.md` — 约束分层。
2. `.agent/reference/ingest-pipeline.md` §compile — 编译纪律。
3. `.agent/reference/card-contracts/body-structure.md` §2 — Buffer 规范。
4. `schemes/default/prompts/compile-*.txt` — 各体裁编译 prompt。

# Workflows

1. 预览分波：
   ```bash
   python -m nexogenesis compile --plan --root .
   ```
2. 生成本波 prompt：
   ```bash
   python -m nexogenesis compile --root .
   ```
3. 串行调用 LLM，保存 response 到 `.nexogenesis/tmp/compile/batch-XXX-response.md`。
4. 检查 response 格式：
   ```bash
   python -m nexogenesis compile --check-responses --root .
   ```
5. 落盘到 Buffer：
   ```bash
   python -m nexogenesis compile --apply --root .
   ```
6. 报告：本波处理文档数、产出 Buffer 数、是否还需下一波。

# Invariants

- 职责：Harness 开窗与闸门；切几块、叫什么、保哪些机制与事实——属 LLM。
- 产出只到 Buffer，不创建/修改 Card 或 Profile。
- 跳过封面/版权/目录等扉页书签。
- 书默认一窗一 prompt，减少赶工薄片。
- `--strict-body` 必须拦截过短/空正文。

# Anti-patterns

- 把 compile 做成逐段转卡的批处理器。
- 手写脚本大修 response 格式。
- 在 compile 阶段就让 LLM 写 Card。
- 产出无命名、无质料的 Buffer。
