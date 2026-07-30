# 约束分层：AGENTS · Skills · 环节约束

　　版本：2026-07-30（对应 tag 锚点 `v0.16-pre-constraint-layers` 之后）  
　　目的：避免把一切规程塞进 `AGENTS.md`；让「怎么跑」「怎么想」「怎么写」各有落点。

## 三层

| 层 | 落点 | 管什么 | 不写什么 |
|----|------|--------|----------|
| **宪法** | [`AGENTS.md`](../AGENTS.md) | 底座主权、聚合涌现、写入闸门、类型一览、CLI 索引、权限 | 逐步操作清单、完整卡片槽正文 |
| **Skills** | [`.agent/skills/`](../.agent/skills/) | Agent 编排剧本（跨工具可用）：何时调 CLI、如何确认、思维体纪律 | 与 prompt/正例重复的长槽表 |
| **环节约束** | `schemes/default/prompts/`、`body-structure`、`card-exemplars`、`validate` | 真正喂给模型的语义质量 + 确定性校验 | Agent 菜单与 git 流程 |

## 两条 Skill 族

### 记忆体（材料 → 结构）

- `nexo-compile` — Inbox 分波编译  
- `nexo-digest` — 骨架滋养式消化  
- `nexo-construct` — 结构校准（镜头）

### 思维体（思考 → 涌现）

- `nexo-talk` — 默认对话：retrieve + STM，分析留对话，不默写卡  
- `nexo-emerge` — 「记一下」/强信号：候选确认后 `write --batch`  
- `nexo-judge` — 高风险深判：有限透镜、定位而非裁决真假  

细则见 [`.agent/skills/*/SKILL.md`](../.agent/skills/)；注意力设计见 `docs/2026-07-28-thinking-body-attention-design.md`。  
　　路径用 `.agent/` 而非 `.cursor/`，便于 Cursor 以外的 Agent 运行时共用同一套剧本。

## DRY

　　原则只在一处写全：写法 → `body-structure` + `card-exemplars`；摄入语义 → `prompts/*.txt`；编排 → skills；AGENTS 只指针。
