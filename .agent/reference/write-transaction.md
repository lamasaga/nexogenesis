---
scheme: "default"
version: "0.4.0"
updated: "2026-07-30"
---

# write --batch 事务规则

　　`write` 是 P0 核心，所有对底座的实质写入（新建/修改卡片、追加问题清单、追加 Profile 字段、追加 Journal）必须通过 `python -m nexogenesis write --batch <file>` 完成。

## 执行顺序

1. 读取 batch YAML；
2. 校验 batch 自身格式；
3. 把每个写入项写到临时文件；
4. 运行完整校验（schema、幽灵链接、orphan、theory 失效边界等）；
5. 校验通过：原子移动临时文件到正式位置 → 追加 Journal → 重新生成索引；
6. 校验失败：删除临时文件，不追加 Journal，不更新索引，返回可读错误。

## batch 文件示例

```yaml
operation:
  id: "2026-07-24-143052-capture"
  source: "对话 2026-07-24"
  approved_by: "user"

writes:
  - target: "card"
    id: "feedback-gap-actionable"
    type: "claim"
    title: "教学反馈应优先指出可操作差距"
    domains: ["teaching"]
    origin: "user"
    maturity: "growing"
    lifecycle: "active"
    body: |
      教师在给出反馈时，应明确指出学生当前表现与目标之间的差距，并提供可操作的建议。
    sources:
      - "2026-07-24 用户对话"
    created: "2026-07-24"
    updated: "2026-07-24"

  - target: "profile_question"
    question: "怎样区分有效反思与自我感动？"
    added_at: "2026-07-24"

  - target: "profile_field"
    file: "领域理念.md"
    section: "核心立场"
    content: "市场化转型国家的制度摩擦常被低估"
    sources:
      - "《某书》第 4 章"
```

## 写入安全

- 所有 YAML 用 `yaml.safe_load` 解析；
- ID 与路径穿越检查（id 允许汉字、字母、数字、连字符 `-`，禁止路径分隔符与危险字符）；
- 先写入 staging 并完整校验，通过后才提交到正式位置；失败不留下半成卡片、问题清单或 Profile 条目；
- `origin: system` 进入 `mature` / `theory_status: active` 须 `approved_by: user` 且 `operation.allow_system_promotion: true`；
- 同一次 batch 对应一个 `operation_id`；digest/construct 用 `operation.consumed_buffers` 声明实际消费的 Buffer 路径。

## 数量上限规则

- `sources` 数量、单卡 `relations` 数量不设 schema 错误；
- 超过建议值 12 时输出 warning；
- 是否真的限制，由真实图结构和使用数据决定。
