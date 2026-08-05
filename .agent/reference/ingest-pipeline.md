---
scheme: "default"
version: "0.4.0"
updated: "2026-07-30"
---

# 文档摄入流水线

　　CLI 完整参数见 `.agent/reference/harness-cli.md`。本文档记录编排纪律与机制说明。

## 典型顺序

```bash
python -m nexogenesis compile --plan --root .    # 预览分波计划
python -m nexogenesis compile --root .           # 生成本波 prompt
# Agent 串行调用 LLM，保存 response 到 .nexogenesis/tmp/compile/batch-XXX-<genre>-response.md
# 命名铁律：与 prompt 同 stem，只把 -prompt 换成 -response（如 batch-001-essay-prompt.md → batch-001-essay-response.md）
python -m nexogenesis compile --check-responses  # 落盘前检查
python -m nexogenesis compile --apply --root .   # 按文件部分成功写入 Buffer

python -m nexogenesis digest --plan --root .     # 预览本波 Buffer
python -m nexogenesis digest --root .            # 生成本波 digest prompt
# Agent 调用 LLM，保存 batch 到 .nexogenesis/tmp/digest/batch.yaml
python -m nexogenesis digest --apply --root .    # 写入 01-Cards/，标记 Buffer 为 digested
# 或：digest --auto

python -m nexogenesis construct --root .         # 默认：结构诊断
python -m nexogenesis construct --lens distinguish --root .
# Agent 保存 batch 到 .nexogenesis/tmp/construct/batch.yaml
python -m nexogenesis construct --apply --root . # 结构优化
# 或：construct --auto --lens <name>
```

## /compile

- 扫描 `00-Inbox/`（默认递归；`--no-recursive` 仅顶层）；源键为相对路径，归档保留子目录；
- 体裁预判：`book` / `paper` / `essay` / `dialogue` / `scrap` / `generic`；
- **阅读窗（Harness）+ 窗内切块（LLM）**：
  - 图书/长文：优先 PDF 目录小节或 Markdown `##`/`###` 开窗；有子节时跳过粗章；跳过封面/版权/目录等扉页书签；若 TOC 仅有前页，则从正文起始页起按页开窗；
  - 论文：有小标题则按节，否则少窗；
  - 对话：按话轮；scrap：段落堆叠；
  - 窗内产出 1～6 个有命名、含质料的 Buffer，块数由模型按内容定；
- 书默认一窗一 prompt，减少赶工薄片；
- LLM 输出极简 frontmatter（`title`/`role`/`source`）+ 自由充实正文；不强制四级槽；
- response 命名 `batch-XXX-<genre>-response.md`，与 prompt 同 stem（只把 `-prompt` 换成 `-response`，genre 段一字不动）；串行生成；`--strict-body` 拦过短/空正文。

## /digest

- 编排见 skill `nexo-digest`；语义见 `schemes/default/prompts/digest.txt`；
- 先消化、后建构；默认一波 `scratch`；
- 主职：骨架滋养 + 建立领域对象；enrich 优先，但遇到真正新、重要且可独立复用的质料时应果断新建 Card；
- 空库须先 domain；写法对齐 exemplars；
- 同步从 Buffer 中提取领域级立场、价值取向、推理模式与反模式，追加到 `02-Profile/`。

## /construct

- 编排见 skill `nexo-construct`；语义见 `schemes/default/prompts/construct.txt`；
- 主职：通盘考虑、合并、调整、升枢纽与张力——不是第二次消化，也不是继续大量新建 Card；
- 原则上不新建 Card；digest 阶段建立的对象由 construct 组织成更干净的结构；只有在通盘考虑后确实缺少枢纽时才允许新建，并须在 operation 中解释原因；
- 默认 diagnose；`--lens` 一次一镜；`--apply-seed-links` 勿当完成态；
- 若涌现出新的领域级理念或思维模型，使用 `target: profile_field` 更新 `02-Profile/`。

## 人机协作边界

- 默认命令只生成 prompt/batch，不自动写入卡片（须 `--apply` 或 `--auto` 二次通过自检）；
- 逐步模式：Agent 在 `--apply` 前检查产物，`operation.approved_by` 记 `user`；
- 自主模式：用户说「开始消化/建构」或显式 `--auto` = 本轮写入授权；Agent 自审中间产物并循环至自检通过；`approved_by` 通常为 `agent`；tmp 下 prompt/batch/报告一律保留供事后分析；
- 未经用户批准，不得把 `origin: system` 的产出直接标为 `mature` 或 `theory_status: active`。
