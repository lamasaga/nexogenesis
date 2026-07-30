---
name: nexo-compile
description: >-
  Runs Nexogenesis Inbox→Buffer compile: wave planning, semantic windows,
  response check then apply. Use when the user says 编译, /compile, Inbox has
  new docs, or asks to process raw materials into Buffer.
---

# nexo-compile（记忆体 · 编译）

## 触发条件

- 用户说「编译」「/compile」「处理 Inbox」；
- `00-Inbox/` 有新文档需要切成 Buffer 质料。

## 步骤

1. `python -m nexogenesis compile --plan --root .`
   - 预览分波计划、体裁预判、阅读窗划分。
2. `python -m nexogenesis compile --root .`
   - 生成本波 prompt 到 `.nexogenesis/tmp/compile/`。
3. 串行调用 LLM，生成 `batch-XXX-response.md`。
4. `python -m nexogenesis compile --check-responses --root .`
   - 检查格式；不合格则重生成，禁止手写脚本大修。
5. `python -m nexogenesis compile --apply --root .`
   - 落盘到 `05-Buffer/<role>/`。
6. 向用户报告：本波文档数、Buffer 数、是否还需下一波。

## 必读文档

- `01-Cards/_meta/body-structure.md` §2（Buffer 规范）
- `AGENTS.md` §8.1（编译纪律）

## 输出

- Buffer 文件写入 `05-Buffer/<role>/`
- 原始文档归档到 `03-Archive/`
- 不创建/修改 `01-Cards/` 或 `02-Profile/`
