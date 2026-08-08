# AGENTS.md — Nexogenesis v1.7 运行时契约

> 版本：v1.7（2026-07-30 约束分层）
> 作用：宪法层——底座主权、权限分层、.agent/ 索引。修订须经用户确认。
> 约束分层：`.agent/reference/constraint-layers.md`

---

## 一、核心原则

1. **底座主权不变量**：约定目录下的 **markdown 是唯一语义事实之源**。删除全部代码与可重建索引，只留 markdown，知识内容零损失。
2. **学科领域思想结构化**：用大模型做**社科领域思想的意义聚合与知识结构涌现**，沉淀可支撑推理、分析、判断的领域知识体；不是自动化拆分书籍/报告的批处理器，也不是个人日记或读书笔记系统。
3. **双层结构：知识体 + 思维体**：`01-Cards/` 与 `05-Buffer/` 构成**知识体**；`nexo-talk|emerge|judge` 等思维体利用该结构进行推理、分析与判断。
4. **Harness 负责过程，LLM 负责语义**：卡片校验、原子写入、索引生成、孤儿检测由 Harness 强制执行；内容好坏、冲突识别、新建/丰富/skip 由 LLM 负责。
5. **统一写入入口**：任何实质写入必须通过 `python -m nexogenesis write --batch <file>`。
6. **复杂度必须有证据**：新增类型、关系、视图、自动化必须说明真实摩擦、最小改动、判断标准和撤回方式。

## 二、目录结构

```text
AGENTS.md                              # 本手册（宪法）
README.md                              # 项目说明
.agent/
├── skills/                            # 编排技能
│   ├── nexo-talk/SKILL.md
│   ├── nexo-emerge/SKILL.md
│   ├── nexo-judge/SKILL.md
│   ├── nexo-compile/SKILL.md
│   ├── nexo-digest/SKILL.md
│   └── nexo-construct/SKILL.md
├── reference/                         # 活契约
│   ├── card-contracts/                # 卡片规范与正例
│   ├── harness-cli.md                 # CLI 参考
│   ├── write-transaction.md           # 写入事务规则
│   ├── ingest-pipeline.md             # 摄入流水线纪律
│   ├── retrieval-design.md            # 双轨检索设计
│   ├── thinking-body.md               # 思维体注意力设计
│   └── constraint-layers.md           # 约束分层说明
└── specs/                             # 设计决策与迭代记录
01-Cards/                              # 知识卡片（不入开发仓，单向镜像纪律见 §七）
02-Profile/                            # 领域级思考特质档案（同上）
03-Archive/                            # 已处理原始材料（同上）
04-OutBox/                             # 分析产物（同上）
05-Buffer/<role>/                      # compile 产出的质料（同上）
06-Journal/                            # 操作大事记（同上）
demo-kb/                               # 演示知识库（29 卡，开发调试与分发演示种子）
nexogenesis/                           # Python 包（harness + runtime/）
web/                                   # Web 前端（React+Vite+TS+Tailwind，FastAPI 托管 dist/）
schemes/default/                       # 默认沉淀方案
```

## 三、权限分层

- **宪法**：`AGENTS.md`
- **编排技能**：`.agent/skills/`
- **活契约**：`.agent/reference/`
- **设计决策**：`.agent/specs/`
- **提示语义**：`schemes/default/prompts/`

统一写入入口：`python -m nexogenesis write --batch <file>`。  
`origin: system` 的卡片未经用户批准不能进入 `mature` 或 `theory_status: active`。

## 四、Skill 索引

| Skill | 触发条件 | 主职 |
|---|---|---|
| `nexo-talk` | 日常对话、分析、思考 | 检索 + STM，归因，分析留对话，不自动写卡 |
| `nexo-emerge` | 「记一下」「/capture」「涌现」 | ≤3 候选 → 用户确认 → write --batch |
| `nexo-judge` | 「深判」「/judge」 | 2–4 透镜，定位而非裁决 |
| `nexo-compile` | 「编译」「/compile」 | Inbox → Buffer |
| `nexo-digest` | 「消化」「/digest」 | Buffer → Card（enrich + 新建） |
| `nexo-construct` | 「建构」「/construct」 | 结构诊断、合并、升枢纽、张力 |

## 五、Reference 索引

| 文档 | 职责 |
|---|---|
| `.agent/reference/card-contracts/body-structure.md` | Buffer / Card 正文结构契约 |
| `.agent/reference/card-contracts/ontology.md` | 卡片类型与关系类型契约 |
| `.agent/reference/card-contracts/card-exemplars/` | 七型写法正例 |
| `.agent/reference/harness-cli.md` | CLI 命令速查表与参数详解 |
| `.agent/reference/write-transaction.md` | `write --batch` 事务规则 |
| `.agent/reference/ingest-pipeline.md` | compile → digest → construct 纪律 |
| `.agent/reference/retrieval-design.md` | 图 + RAG 双轨检索设计 |
| `.agent/reference/thinking-body.md` | 思维体注意力设计 |
| `.agent/reference/constraint-layers.md` | 约束分层说明 |

## 六、Spec 索引

- SPEC目录文档不参与日常运作，只在调整、优化agent自身的时候才关注这个文件夹。


## 七、AI 禁止与必须

### 禁止

- 把 ingest 做成「切书批处理器」。
- 用空心「原文未提及」/标题回声凑格式。
- 绕过 `write --batch` 直接改卡片文件。
- 创建信息稀薄的空卡片。
- 为每篇文档都创建新卡片。
- 在 Inbox 中堆积已处理原始文档。
- 未经用户确认改写 `02-Profile/` 已有条目。
- 删除任何卡片（只能标记 `lifecycle: superseded`/`archived`）。
- 创建幽灵链接。
- 让卡片因无限引用而膨胀。

### 必须

- 以聚合涌现为目标：拥有细节、凝聚思想和信息的质料 → 可独立阅读的卡片结构。
- 优先丰富已有卡片，而非新建卡片；丰富后的卡片拥有更多可解释性和支撑性信息。
- 检测并记录冲突。
- 维护领域卡片的完整性。
- 主动沉淀领域级理念与思维范式到 `02-Profile/`，并标注来源。
- 处理完后归档原始文档。
- 所有 AI 生成的内容标注来源。
- 任何写入须经授权：逐步确认，或用户一句「开始消化/建构」/`--auto` 视为本轮授权。
- **单向镜像纪律（2026-08-08 用户宪法级确认）**：本仓（`-org`）是纯开发仓——只跟踪代码、`.agent/`、`schemes/`、`docs/`、`demo-kb/`，知识体目录（`00-Inbox`/`01-Cards`/`02-Profile`/`03-Archive`/`04-OutBox`/`05-Buffer`/`06-Journal`）一律不入库；本仓必须保持随时可打包分发的干净状态。实践仓承担 `compile`/`digest`/`construct`/`emerge` 全部知识体工作，只从本仓 `pull` 补丁，**永不 push 回 origin**（机械防呆：实践仓 push 远端已设为 DISABLED）。
