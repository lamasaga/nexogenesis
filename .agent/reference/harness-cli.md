---
scheme: "default"
version: "0.4.0"
updated: "2026-07-30"
---

# Harness CLI 参考

　　本文档是 `AGENTS.md` 的操作参考层，记录所有 `python -m nexogenesis` 命令。修订须经用户确认。

> 各 `.agent/skills/*/SKILL.md` 的 Workflows 只列出与本 skill 相关的典型调用顺序；完整参数、默认值与注意事项均以本文档为准。

## 底座维护

| 命令 | 常用选项 | 作用 |
|---|---|---|
| `init` | `--root` | 初始化目录结构、复制 scheme 模板、安装 git pre-commit hook |
| `validate` | `--root` | 校验全部卡片 frontmatter、链接、orphan（pre-commit 亦调用） |
| `index` | `--root` | 生成 `01-Cards/_meta/` 下领域/冲突/理论视图 |
| `write` | `--batch <file>` `--root` | **统一原子写入入口**（卡片、问题清单、Profile 字段、Journal）；成功后自动 `index` + `graph rebuild` + `rag index` |
| `doctor` | `--root` | 目录/契约/hook 检查 + `validate` + 图/RAG 索引陈旧 WARNING |
| `migrate` | `--to <scheme>` `--dry-run` `--root` | scheme 迁移预演 |

## 文档摄入：`compile` → `digest` → `construct`

| 命令 | 常用选项 | 作用 |
|---|---|---|
| `compile` | `--plan` | 预览 Inbox 分波计划（不写 prompt） |
| | `--root` | 生成本波 compile prompt（默认自动分波） |
| | `--check-responses` | 检查 `batch-*-response.*` 格式（不写盘） |
| | `--apply` | 将 response 落盘为 `05-Buffer/`（按文件部分成功） |
| | `--response <file>` | 只检查/apply 指定 response |
| | `--all` `--recursive`/`--no-recursive` `--deep` | 关闭分波 / 是否递归扫 Inbox（默认递归）/ 深度模式（每波 1 篇） |
| | `--max-chars` `--wave-prompts` `--wave-docs` | 分波规模控制 |
| | `--genres "a.md=paper,..."` | 体裁覆盖 |
| | `--strict-body` | 语义槽缺失升为错误 |
| `digest` | `--plan` | 预览本波 Buffer 选择与字符预算 |
| | `--root` | 生成本波 digest prompt（默认 `status=scratch`，分波） |
| | `--apply` | 应用 `.nexogenesis/tmp/digest/batch.yaml` 写入卡片 |
| | `--auto` | 无 batch → prompt+规程；有 batch → 自检通过后 apply |
| | `--wave-buffers N` `--deep-cards N` | 本波 Buffer 数 / 深读卡数 |
| | `--status scratch` `--all-scratch` | Buffer 状态过滤 / 调试全量 |
| `construct` | （默认） | 结构诊断：`lenses-report.md` + graph analyze + 可执行 `structure-ops-draft.md` |
| | `--diagnose` | 显式只诊断（同默认） |
| | `--apply-seed-links` | 应用确定性补边：空 `relations` → `applies-to` 所属 domain |
| | `--lens cluster\|distinguish\|articulate\|cross_source` | 单镜头 prompt（禁止 `all`） |
| | `--plan` | 预览本镜头深读对象 |
| | `--apply` | 应用 `.nexogenesis/tmp/construct/batch.yaml` |
| | `--auto` | 无 lens → 诊断+自动 seed-links+suggested-lenses；有 lens+batch → 自检 apply |
| | `--deep-cards N` `--wave-buffers N` | 镜头模式深读规模 |

**典型顺序：**

```bash
python -m nexogenesis compile --plan --root .
python -m nexogenesis compile --root .
# LLM → batch-XXX-response.md → compile --check-responses → compile --apply

python -m nexogenesis digest --plan --root .
python -m nexogenesis digest --root .
# → batch.yaml → digest --apply 或 digest --auto

python -m nexogenesis construct --root .
# → lenses-report / suggested-lenses → construct --lens <name> → batch.yaml → construct --auto --lens <name>
```

## 双轨检索：结构图 + 质料 RAG

| 命令 | 常用选项 | 作用 |
|---|---|---|
| `graph rebuild` | `--root` | 从卡片重建结构图索引 |
| `graph stats` | `--root` | 节点/边统计 |
| `graph analyze` | `--rebuild` `--root` | orphan、conflict 缺口、桥接点 → `structure_ops.json` + 报告 |
| `graph retrieve` | `--query` `--seed` `--hops` `--max-nodes` `--out` | 结构子图检索，写入 Context Package |
| `graph export` | `--center <id>` `--hops` `--out` `--rebuild` | 导出 GraphML |
| `rag index` | `--full` `--kinds` `--root` | 建/增量更新 FTS 索引 |
| `rag stats` | `--root` | 语料块数与索引时间 |
| `rag search` | `--query` `--kinds` `--top` `--root` | 质料检索 |
| `retrieve` | `--query` `--mode talk\|answer\|digest\|construct\|judge` | 统一双轨入口：结构子图 + RAG 质料 |
| `memory start\|status\|update\|override\|end` | `--focus` `--cite` `--tension` | 短期记忆会话卷 |
| `attention show\|validate` | `--profile` `--print-yaml` | 注意力配置 |
| `signal` | `--text` `--bump-turn` | 强信号评估（只建议，不写卡） |

**检索典型用法：**

```bash
python -m nexogenesis graph rebuild
python -m nexogenesis rag index
python -m nexogenesis memory start --title "今日对话"
python -m nexogenesis retrieve --query "…" --mode talk --root .
python -m nexogenesis signal --text "记一下"
```

## 速记（一行版）

```bash
python -m nexogenesis init | validate | index | doctor
python -m nexogenesis write --batch <file>
python -m nexogenesis compile [--plan|--check-responses|--apply]
python -m nexogenesis digest [--plan|--apply|--auto]
python -m nexogenesis construct [--lens|--apply|--auto]
python -m nexogenesis graph rebuild|stats|analyze|retrieve|export
python -m nexogenesis rag index|stats|search
python -m nexogenesis retrieve --query "…" --mode talk
python -m nexogenesis memory start|status|update|override|end
python -m nexogenesis attention show|validate
python -m nexogenesis signal --text "…"
```
