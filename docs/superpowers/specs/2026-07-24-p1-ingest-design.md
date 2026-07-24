# Nexogenesis P1 文档摄入流水线设计

> 版本：2026-07-24  
> 范围：compile → digest → construct 三阶段，适配新扁平结构与 7 型卡片  
> 状态：设计稿，待确认后进入实现计划

---

## 一、目标

在 P0 的对话-捕获-回答闭环之上，增加文档批量摄入能力：

```text
00-Inbox/ 原始文档
    → /compile  → 05-Buffer/ 原子片段
    → /digest   → 01-Cards/ 卡片 + 02-Profile/ 问题
    → /construct→ 01-Cards/ 领域调整 + 关系补全 + Profile 更新
```

P1 不直接调用 LLM API，而是让 harness 生成 prompt/batch，由 code agent 调用 LLM 并把结果回写到指定目录，再由 harness 执行 `--apply` 完成落地。这样既能利用本地 code agent 完成大模型交互，又保证未来可以逐步替换为 API 调用而不改整体架构。

---

## 二、核心原则

1. **Harness 负责编排与校验，LLM 负责语义**：genre 检测、chunk、prompt 生成、结果解析、目录移动由代码完成；内容提取、冲突识别、重要性判断由 LLM 完成。
2. **一键流水线 + 可审查中间产物**：默认命令一步生成所有需要的 prompt/batch，但中间文件留在 `.nexogenesis/tmp/`，Agent 可以查看、修改、确认。
3. **复用 v4.0 已验证资产**：把 `思维涌现mainV4/scripts/compile_lib/` 迁移到 `nexogenesis/ingest/`，再按新 schema 改造，保留 87 个测试覆盖的核心逻辑。
4. **与 P0 写入口一致**：digest/construct 最终产物是标准 `write --batch` YAML，Agent 确认后统一走 `nexogenesis write --batch`。
5. **可演进为无人值守**：当前架构留出 LLM driver 接口，未来实现 `LLMClient` 后，`--auto` 模式可直接调用 API，无需 Agent 手动回写。

---

## 三、目录结构变化

```text
nexogenesis/
├── ingest/                    # 新增：文档摄入引擎（从 v4.0 迁移）
│   ├── __init__.py
│   ├── ingest.py              # 扫描 Inbox、genre 检测
│   ├── chunker.py             # 分块
│   ├── batch_runner.py        # batch 分组与 prompt 生成
│   ├── prompt_formatter.py    # 把 LLM 返回解析为 Buffer / batch
│   └── prompts/               # 各体裁 prompt 模板（从 scheme 加载）
├── commands/
│   ├── compile.py             # 新增
│   ├── digest.py              # 新增
│   └── construct.py           # 新增
...
schemes/default/
├── scheme.md
├── ontology-template.md
├── profile-template.md
├── migration.md
└── prompts/                   # 新增：默认方案的 prompt 模板
    ├── compile-book.txt
    ├── compile-paper.txt
    ├── compile-essay.txt
    ├── compile-dialogue.txt
    ├── compile-scrap.txt
    ├── digest.txt
    └── construct.txt
```

`05-Buffer/` 子目录从 v4.0 的 10 种改为 7 种：

```text
05-Buffer/
├── domain/
├── claim/
├── phenomenon/
├── model/
├── method/
├── entity/
└── conflict/
```

---

## 四、类型映射

v4.0 10 型 → P1 7 型：

| v4.0 类型 | P1 类型 | 说明 |
|---|---|---|
| `domain` | `domain` | 不变 |
| `notion` / `principle` | `claim` | 立场、原则统一为 claim；强度在正文中表达 |
| `phenomenon` | `phenomenon` | 不变 |
| `model` | `model` | 不变 |
| `method` | `method` | 不变 |
| `entity` / `group` | `entity` | 群体作为 entity 的基数属性，不独立成类型 |
| `conflict` | `conflict` | 不变 |
| `note` | `claim`（seed） | 未成熟想法降级为 seed claim，或 discard |

关系类型沿用 P0 的 8 种：
`extends`、`supports`、`conflicts-with`、`involves`、`example-of`、`applies-to`、`based-on`、`influences`。

---

## 五、Buffer 规范（更新版）

Buffer 文件是 compile 的原子输出，digest 的输入。文件名：`YYYY-MM-DD-HHMMSS-<关键词>.md`。

```yaml
---
title: "认知脚手架"
type: "claim"                    # 7 种之一
status: "scratch"                # scratch | digested | constructed
created: "2026-07-24T09:36:25"
updated: "2026-07-24T09:36:25"
source: "《某书》第 4 章 / p.12"
genre: "book"                    # 体裁：book | paper | essay | dialogue | scrap
perspective: "external"          # self | external
proposed_domains:                # 可选：LLM 建议的领域
  - "teaching"
proposed_maturity: "seed"        # 可选
---
```

正文要求：
- Markdown；
- 不使用 `[[ ]]` 链接，用加粗表示跨引用；
- 每个片段只表达一个可沉淀的思想单位。

---

## 六、命令设计

### 6.1 `python -m nexogenesis compile`

默认行为：扫描 `00-Inbox/`，生成 prompt 文件到 `.nexogenesis/tmp/compile/`。

```bash
python -m nexogenesis compile [--root .] [--deep] [--genres "a.md=essay,b.md=scrap"]
python -m nexogenesis compile --apply [--root .]
```

**阶段 1（默认）**：
1. 扫描 `00-Inbox/`，过滤 `.md`、`.txt`、`.markdown`、`.pdf`；
2. 对每篇文档做 genre 检测（启发式）；
3. 按体裁分块；
4. 生成 LLM prompt（按 genre 模板），要求 LLM 输出符合 Buffer schema 的 YAML 片段列表；
5. 把 prompt 写到 `.nexogenesis/tmp/compile/<doc-id>-prompt.md`；
6. 输出操作指南，告诉 Agent：调用 LLM → 把返回保存到 `.nexogenesis/tmp/compile/<doc-id>-response.yaml` → 运行 `--apply`。

**阶段 2（`--apply`）**：
1. 读取所有 response YAML；
2. 解析为 Buffer frontmatter + body；
3. 校验 Buffer schema 和类型；
4. 原子写入 `05-Buffer/<type>/`；
5. 把原始文档移动到 `03-Archive/`；
6. 追加 Journal；
7. 运行 `validate`。

### 6.2 `python -m nexogenesis digest`

```bash
python -m nexogenesis digest [--root .] [--status scratch]
python -m nexogenesis digest --apply [--root .]
```

**阶段 1（默认）**：
1. 读取 `05-Buffer/` 中 `status: scratch` 的片段；
2. 读取现有 `01-Cards/` 和 `02-Profile/问题清单.md`；
3. 生成 digest prompt，要求 LLM 输出：
   - 哪些 Buffer 可以 enriching 已有卡片；
   - 哪些需要新建卡片；
   - 哪些产生冲突；
   - 哪些问题追加到问题清单；
4. 产物写到 `.nexogenesis/tmp/digest/batch.yaml`（标准 `write --batch` 格式）。

**阶段 2（`--apply`）**：
1. 把 `batch.yaml` 提交给 Agent 确认；
2. 运行 `nexogenesis write --batch .nexogenesis/tmp/digest/batch.yaml`；
3. 把已消费的 Buffer 状态改为 `digested`；
4. 追加 Journal。

> 注意：`--apply` 本身只是一个命令开关，它不替代人工确认。Agent 必须在运行 `--apply` 前检查 batch/response 内容，并在 `operation.approved_by` 中记录确认来源。未来若实现 `--auto` 模式，才由 harness 自动调用 LLM 并直接写入。

### 6.3 `python -m nexogenesis construct`

```bash
python -m nexogenesis construct [--root .]
python -m nexogenesis construct --apply [--root .]
```

**阶段 1（默认）**：
1. 读取全部 `01-Cards/` 和 `05-Buffer/`；
2. 识别结构张力：冗余、分裂、链接空洞、领域归属冲突；
3. 生成 construct prompt，要求 LLM 输出 batch：
   - 新建/调整 `domain` 卡；
   - 补全 `relations`；
   - 调整 `domains` 字段；
   - 更新 `02-Profile/`（如检测到新模式）。
4. 产物写到 `.nexogenesis/tmp/construct/batch.yaml`。

**阶段 2（`--apply`）**：
1. Agent 确认 batch；
2. `write --batch` 写入；
3. 把相关 Buffer 状态改为 `constructed`；
4. 追加 Journal。

---

## 七、LLM 返回格式

### Buffer response（compile）

```yaml
buffers:
  - title: "认知脚手架"
    type: "claim"
    genre: "book"
    perspective: "external"
    proposed_domains:
      - "teaching"
    body: |
      教师在学生最近发展区内提供临时支持，随后逐步拆除...
    source: "《心智的构建》第 4 章 / p.89"
```

### Batch response（digest/construct）

标准 `write --batch` YAML：

```yaml
operation:
  id: "2026-07-24-165432-digest"
  source: "05-Buffer 消化"
  approved_by: "user"

writes:
  - target: "card"
    id: "cognitive-scaffolding"
    type: "claim"
    title: "认知脚手架"
    ...
  - target: "profile_question"
    question: "..."
    added_at: "2026-07-24"
```

---

## 八、Prompt 模板管理

Prompt 模板放在 `schemes/default/prompts/`。这样做的好处：

- 方案层可以替换 prompt（未来不同 scheme 不同策略）；
- 模板使用 Jinja2 占位符，如 `{{ genre }}`、`{{ chunks }}`、`{{ ontology }}`；
- 加载顺序：`schemes/<active>/prompts/` → 若不存在则 fallback 到包内默认模板。

---

## 九、测试策略

1. **单元测试**：迁移 v4.0 的 87 个测试到 `tests/ingest/`，更新类型集合与期望；
2. **集成测试**：
   - `test_compile_command.py`：`00-Inbox` → prompt → mock response → `05-Buffer`；
   - `test_digest_command.py`：`05-Buffer` → `batch.yaml`；
   - `test_construct_command.py`：卡片集合 → `batch.yaml`；
3. **端到端测试**：真实 LLM 响应样本（fixture）跑通 `--apply`。

---

## 十、风险与延后

| 风险 | 缓解 |
|---|---|
| v4.0 代码与 P0 schema 差异大，迁移时丢失边界逻辑 | 先整体迁移，再逐测试修复，不一次改完 |
| LLM 返回 YAML 不稳定 | 使用 YAML 安全解析 + 错误恢复 + 人工确认 |
| 一键流水线隐藏中间状态 | 默认保留 `.nexogenesis/tmp/` 全部产物 |
| Profile 更新未经确认 | construct batch 中 Profile 写入需 Agent 显式批准 |
| 体裁检测误判 | Agent 可用 `--genres` 覆盖 |

---

## 十一、P1 验收标准

1. `compile` 能把 `00-Inbox/` 的示例文档生成有效的 `05-Buffer/` 片段；
2. `digest` 能把 Buffer 生成标准 `write --batch` YAML；
3. `construct` 能把卡片集合生成结构优化 batch；
4. `--apply` 会调用 `write --batch`，失败时回滚；
5. 原始文档在 compile 成功后移到 `03-Archive/`；
6. 全部新增测试通过；
7. `AGENTS.md` 和 `schemes/default/` 文档更新，说明三阶段用法。
