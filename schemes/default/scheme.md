---
scheme_id: "default"
version: "0.1.0"
name: "默认沉淀方案"
based_on: "思维涌现mainV4"
---

# 默认沉淀方案

适用于个人思想沉淀与一般性知识管理。卡片类型 7 种，关系 8 种。

## 文档摄入流水线

本方案提供 `prompts/` 下的体裁专属 prompt 模板，驱动 `compile` → `digest` → `construct` 三阶段：

- `compile-*.txt`：把 00-Inbox 文档拆分为 05-Buffer 原子片段；
- `digest.txt`：把 Buffer 片段沉淀为 01-Cards 卡片或问题清单条目；
- `construct.txt`：基于当前卡片和 Buffer 做结构整理。

模板使用 Jinja2 渲染，可在本 scheme 内按需覆盖。
