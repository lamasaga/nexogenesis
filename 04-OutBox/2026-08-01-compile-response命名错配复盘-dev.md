# Compile 复盘：response 命名错配导致进度未记账

> 日期：2026-08-01  
> 场景：首次分波编译 `00-Inbox/` 经济学课文（本波：第08章）  
> 产物状态：Buffer 已写入成功；进度曾未记账，后已人工补记  
> 性质：过程事故分析（非 Card；默认不作已定结论）

---

## 1. 一句话结论

　　本波 Buffer **写盘成功**，但因 response 文件名**漏写体裁段**（`essay`），Harness 无法把「已 apply 的文件」与 manifest 里的 prompt 对齐，于是判定 `wave_complete=False`，**不更新 `progress.json`、不归档原文**。表面像「编译没完成」，实际是「质料已落、账没记上」。

---

## 2. 时间线：发生了什么

1. `compile --plan`：38 篇 Inbox；默认每波约 1 篇、最多 4 个 prompt；首波选中第08章（按字数较短优先，非章序）。
2. `compile`：生成 4 个 prompt，文件名为  
   `batch-001-essay-prompt.md` … `batch-004-essay-prompt.md`。
3. Agent 按 skill / 文档中的简写，将回复存为：  
   `batch-001-response.md` … `batch-004-response.md`（**缺少 `-essay-`**）。
4. `compile --check-responses`：格式检查 **全部 OK**（检查只认 `batch-*-response.*` glob，不校验是否与 prompt 体裁段对齐）。
5. `compile --apply`：  
   - 写出 **11** 条 Buffer（落在 `05-Buffer/`）；  
   - 成功后删除 response 文件；  
   - 报告 `wave_complete=False`，`archived=0`。
6. 再跑 `--plan`：第08章仍显示 `done_units=0`，仍被选为本波——进度未前进。
7. 核对 `wave-manifest.json` 后定位错配（见下节）；人工把 `applied_batch_files` 对齐并 `mark_units_completed`。补记后发现该章共 **10** 个阅读窗，本波只覆盖 **8** 个，仍剩 **2** 个待下一波（属正常分波，不是同一事故）。

---

## 3. 根因：文件名映射断了一截

### 3.1 Harness 如何判定「本波完成」

　　`compile --apply` 大致逻辑：

- 对每个成功的 response，用 `_response_to_prompt_name` 还原「对应的 prompt 名」，记入 `applied_batch_files`；
- 与 manifest 的 `batch_files`（真实 prompt 列表）做集合包含判断；
- **仅当** `expected ⊆ applied` 时：`wave_complete=True`，才写入 `progress.json` 的 `completed_unit_ids`，并在该源无剩余窗时归档 Inbox。

### 3.2 实际映射结果

| 真实 prompt（expected） | Agent 写的 response | 映射得到的 applied |
|---|---|---|
| `batch-001-essay-prompt.md` | `batch-001-response.md` | `batch-001-prompt.md` |
| `batch-002-essay-prompt.md` | `batch-002-response.md` | `batch-002-prompt.md` |
| … | … | … |

　　转换规则（代码注释示例）期望的是：

```text
batch-001-scrap-response.md  →  batch-001-scrap-prompt.md
```

　　即：**序号 + 体裁 + response/prompt** 成对出现。漏掉体裁后，applied 与 expected 永不交集对齐，`wave_complete` 恒为假。

### 3.3 为何「检查通过」却「进度失败」

| 步骤 | 是否校验「与 prompt 同名结构」 | 结果 |
|---|---|---|
| `--check-responses` | 否；只解析 Buffer 块格式 | 全绿 |
| `--apply` 写 Buffer | 否；按文件内容落盘 | 成功 |
| `--apply` 收尾记账 | **是**；必须与 `batch_files` 对齐 | 失败 |

　　因此事故形态是：**质料层成功、进度层静默失败**，容易误判为「还要重跑整波」，若盲目重跑同内容会 **重复写入 Buffer**。

---

## 4. 文档侧诱因（简写过度）

　　多处编排文档把 response 写成：

```text
batch-XXX-response.md
```

　　包括 `nexo-compile` skill、`ingest-pipeline.md`、`harness-cli.md` 示例。对 Agent 而言，这会被理解成字面文件名；而实际 prompt 为：

```text
batch-XXX-<genre>-prompt.md
```

　　体裁常见值：`essay` / `book` / `paper` / `scrap` / `dialogue` / `generic`。本次课文单章被判为 `essay`，故必须带 `-essay-`。

---

## 5. 如何避免（操作清单）

### 5.1 命名铁律（每次写 response 前）

1. 看 `.nexogenesis/tmp/compile/` 里真实 prompt 名；  
2. 只把 `-prompt` 换成 `-response`，**其余字符一字不动**：

```text
batch-001-essay-prompt.md  →  batch-001-essay-response.md
batch-002-book-prompt.md   →  batch-002-book-response.md
```

3. **禁止**写成 `batch-001-response.md`（除非 prompt 本身就是 `batch-001-prompt.md`）。

### 5.2 Apply 后必读的两行信号

　　`--apply` 结束时确认：

- `wave_complete=True`（本波记账成功）；  
- 若该文档全部窗已完成，应看到 `archived≥1`（原文进 `03-Archive/`）。

　　若出现 `wrote>0` 但 `wave_complete=False`：

1. **先不要**对同一波内容再生成一套 response 并 apply（防重复 Buffer）；  
2. 打开 `wave-manifest.json`，对比 `batch_files` 与 `applied_batch_files`；  
3. 若仅差体裁段：用正确文件名重放 response（或对齐 applied 后补跑进度逻辑），再确认 `progress.json` 与 `--plan` 的 `done_units`。

### 5.3 建议补强（产品/契约，非本波已改代码）

| 优先级 | 改动 | 作用 |
|---|---|---|
| 高 | skill / `ingest-pipeline` / CLI 示例改为 `batch-XXX-<genre>-response.md`，并写一句「与 prompt 同 stem」 | 从源头消歧 |
| 中 | `--check-responses` 增加：response 能否映射到当前 manifest 的某个 `batch_files`；否则 warning/error | 落盘前拦住 |
| 中 | `--apply` 在 `wrote>0 && not wave_complete` 时打印明确 diff（expected vs applied） | 降低静默失败 |
| 低 | 对「仅缺 genre 段」的旧式 `batch-NNN-response.md` 做容错匹配 | 兼容误命名 |

---

## 6. 与「章未归档」相关的正常现象（勿与事故混淆）

　　第08章在 Harness 下被切成 **10** 个阅读窗；默认 `wave_prompts≤4` 时，一波最多覆盖 8 个窗（本波 4 prompt × 每 prompt 至多 2 窗）。因此：

- 即使命名正确、`wave_complete=True`，该章也可能 **尚未** `archived`，`--plan` 仍显示同一篇且 `done_units=8`；  
- 需再跑一波处理剩余窗，全部完成后才会归档。

　　「多波才归档」是设计行为；「写了 Buffer 但 `done_units` 仍为 0」才是本次事故特征。

---

## 7. 本波处置摘要（供对照）

| 项 | 状态 |
|---|---|
| Buffer | 已写入 11 条（meaning-unit / tension） |
| 错误命名的 response | apply 后已删除 |
| `progress.json` | 已人工补记 8 个 unit id |
| 第08章 Inbox | 当时未归档（仍有 2 窗 pending，属正常） |
| 后续编译 | response **必须**用 `batch-XXX-essay-response.md` 形式 |

---

## 8. 可复制的自检命令

```powershell
python -m nexogenesis compile --check-responses --root .
python -m nexogenesis compile --apply --root .
# apply 后立刻：
python -c "import json; from pathlib import Path; m=json.loads(Path('.nexogenesis/tmp/compile/wave-manifest.json').read_text(encoding='utf-8')); print('expected', m.get('batch_files')); print('applied', m.get('applied_batch_files')); print('status', m.get('status'))"
python -m nexogenesis compile --plan --root .
```

　　自检通过标准：`applied` 与 `expected` 集合一致（或 applied ⊇ expected），且下一轮 `--plan` 的 `done_units` 相对本波有增加。
