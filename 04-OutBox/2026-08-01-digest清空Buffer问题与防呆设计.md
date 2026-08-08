# Digest 复盘：清空 89 片 Buffer 过程中的问题与防呆设计

> 日期：2026-08-01  
> 场景：消化曼昆第05–08章编译产物（89 scratch → digested；空库 bootstrap → 16 张 Card）  
> 终态：`digest --plan` 报「没有待消化的 Buffer」；domain×1 / model×5 / claim×8 / conflict×2  
> 性质：过程事故与摩擦分析（非 Card；默认不作已定结论）  
> 关联：`04-OutBox/2026-08-01-compile-response命名错配复盘.md`（compile 侧命名事故）

---

## 1. 一句话结论

　　消化主路径能跑通，但摩擦集中在五类：**YAML 字面量被静默解析错**、**自检与写入契约不一致**、**空库首波选题顺序不利于骨架**、**enrich 导致 sources 膨胀**、**多波人工编排成本高**。多数可用「契约对齐 + 落盘前硬校验 + 分波启发式」在设计层消掉，而不必靠事后修 batch。

---

## 2. 本轮消化时间线（压缩）

| 波次 | 动作摘要 | 结果 |
|---|---|---|
| Wave01 | 空库：建 domain + 税负 claim + 最低工资两造 claim + conflict；消费 6 tension；skip 劳动税/拉弗 tension | 成功写入 5 卡 + Profile |
| Wave02 | model「税收无谓损失机制」+ 拉弗 conflict 结构；enrich domain；消费 12 | 成功 |
| Wave03 | model「竞争市场总剩余最大化」等；含 `sources` 冒号未加引号 | **首次 apply 失败**；修 YAML 后重试成功 |
| Wave04–07 | 弹性模型、供给应用、价格管制、EITC 等；大量 enrich | 成功；多卡 `sources>12` warning |
| 终态 | 89 digested；16 cards | 清空 scratch |

---

## 3. 问题分类与根因

### 3.1 【硬故障】YAML `sources` 含冒号 → 解析成 mapping

**现象**

```text
schema error: {'第07章 … / 7-4 Conclusion': 'Market Efficiency and Market Failure'}
is not of type 'string' at ['sources', 0]
```

**根因**

　　未加引号的 YAML 行：

```yaml
- 第07章 … / 7-4 Conclusion: Market Efficiency and Market Failure
```

　　被解析为「单键字典」，而 schema 要求 `sources` 元素为 `string`。`self_check_batch` **不检查** sources 元素类型，故「自检通过 / apply 失败」。

**影响**

　　整批 write 事务回滚（设计正确：无半提交）；但 Agent 易在失败后立刻 `digest --root` 覆盖 prompt，若同时覆盖 batch 会丢失已修好内容。

**如何避免（设计）**

| 层 | 建议 |
|---|---|
| Harness | `self_check_batch` / `--apply` 前校验：一切 `sources[]`、`relations[].note` 等须为 str；失败给出「第 i 条疑似未加引号冒号」 |
| Prompt / skill | digest 输出纪律加粗：**凡含 `:` 的标量一律双引号**；给正例与反例 |
| 工具 | 提供 `digest --lint-batch` 专检 YAML 类型陷阱（sources、domains、id） |
| Agent | apply 前固定跑一段「bad sources 探测器」（本轮后期已养成） |

---

### 3.2 【契约裂缝】`self_check` 不认 `profile_field`，`write` 却支持

**现象**

　　`self_check_batch(..., mode="digest")` 对 `target: profile_field` 报「未知 target」；同文件经 `digest --apply` → `write --batch` 可成功写入 Profile。

**根因**

　　`batch_auto.self_check_batch` 只显式放行 `card` 与 `profile_question`；`write.py` 另支持 `profile_field`。`--auto` 路径若严格依赖 self_check，会**误拒合法 Profile 更新**；逐步 `--apply` 则绕过该裂缝。

**如何避免（设计）**

- 单一真相：`self_check` 的 target 枚举与 `write` 对齐（至少 `card` / `profile_field` / `profile_question`）。
- 文档：`write-transaction.md` 与 digest skill 同步列出允许 target，避免 Agent 以为 Profile 只能手改。

---

### 3.3 【编排摩擦】空库首波优先抽 tension，骨架倒置

**现象**

　　`--plan` 在 `bootstrap=True` 时本波 8 片几乎全是 `tension`（最低工资、拉弗、器官市场、奢侈税等），而「消费者剩余 / 无谓损失 / 弹性定义」等 meaning-unit 大量暂缓。

**根因**

　　分波选择未区分「建骨架所需质料」与「依赖骨架的对立质料」。conflict 需要两造 claim/model；tension 先到时，要么过早建冲突结构，要么 skip 等后波——本轮对劳动税/拉弗做了人为 skip，增加认知负担。

**如何避免（设计）**

| 策略 | 说明 |
|---|---|
| Bootstrap 启发式 | 空库首波优先 `meaning-unit`（及 profile-seed），tension 权重降低或封顶（如首波 ≤2 tension） |
| 依赖提示 | plan 报告：「本波含 conflict 候选但尚无同主题 model/claim → 建议先消费机制类 Buffer」 |
| Prompt | bootstrap 段写死顺序：domain → 核心 model/method → 再 conflict |
| 可选 CLI | `--prefer-roles meaning-unit,method` 或 `--defer-roles tension` |

---

### 3.4 【质量张力】「建议新建 ≤N」vs conflict 的最小卡组

**现象**

　　质量提示「12 Buffer → 建议新建 ≤4」。但一张可用的 `conflict` 至少需要 **conflict + 两造 claim/model**（或已有卡可 involves），空库时很容易「一张冲突 = 三张新卡」，与 ≤N 软上限打架。

**根因**

　　提示按 Buffer 数线性缩放，未按「结构单元」（一个对立、一个模型）计量。

**如何避免（设计）**

- 提示改为：**建议 ≤K 个结构单元**（domain 升级 / 一个 model / 一组 conflict bundle 计 1 单元）。
- 允许「conflict bundle」在 batch 内一次写入多卡但只计 1 次新建预算。
- construct 阶段再合并重复 claim；digest 不必为压 N 而把对立糊进 domain「内在张力」了事（本轮部分 tension 进 domain，可读性尚可，但复用性弱于独立 conflict）。

---

### 3.5 【慢性问题】反复 enrich → `sources` 超过建议值 12

**现象**

　　后期 apply 多次 WARNING：`市场效率与政策干预`、`竞争市场总剩余最大化`、`需求价格弹性与总收益判别` 等 sources 数量 >12。未阻断写入。

**根因**

　　每波 enrich 追加 Buffer 路径与章节锚点；无自动归并；domain 成为「万用挂靠点」后膨胀更快。

**如何避免（设计）**

| 层 | 建议 |
|---|---|
| Digest 纪律 | enrich 时 sources **重写为压缩列表**：1 条教材总述 + 若干代表性 Buffer，而非无限 append |
| Harness | warning 时提示「本波请压缩 sources」；可选 `--strict-sources` 升错误 |
| 卡片设计 | domain 的 sources 只保留领域级出处；实例细节进 instance 卡 |
| Construct | 增加 lens：`compact-sources` / `drain-domain-dump` |

---

### 3.6 【操作风险】apply 失败后立刻 `digest --root` 可能冲掉 batch

**现象**

　　Wave03 失败后同一次命令链里执行了 `digest --root`，prompt 按「未消费 Buffer」重生成（正确），但若 Agent 或脚本覆盖 `batch.yaml`，已部分修好的 YAML 会丢。

**如何避免（设计）**

- skill 写明：**apply 失败 → 先修 batch → 再 apply；禁止失败同回合无条件 regenerate**。
- Harness：`digest --root` 若发现 `batch.yaml` 存在且 `operation.id` 对应当前未消费集合，则拒绝覆盖或写入 `batch.yaml.bak`。
- `digest --apply` 失败输出中附带「保留 batch 路径，勿立即 --root」。

---

### 3.7 【认知负荷】多波清空成本高，子代理易引入格式债

**现象**

　　89 片约 7 波；靠子代理写 `batch.yaml` 加速，但仍出现 sources 引号事故；父代理必须保留「类型探测器」闸门。

**根因**

　　digest 语义重、YAML 脆、分波状态在 tmp 文件；缺少「生成 → lint → apply」一条龙命令。

**如何避免（设计）**

```text
digest --auto 理想闭环：
  无 batch → 写 prompt + runbook
  有 batch → lint（含 sources 类型）→ self_check（target 对齐）→ write --batch → 标 digested
```

　　Agent 规程改为：**禁止跳过 lint**；子代理交付物必须声明「已对 sources 做 str 校验」。

---

### 3.8 【轻摩擦】终端编码与路径显示

**现象**

　　Windows PowerShell 默认代码页下，`print` 中文卡 id 乱码；文件本身 UTF-8 正常。

**如何避免**

　　脚本统一 `sys.stdout.reconfigure(encoding="utf-8")` 或写到 UTF-8 报告文件再读；不把终端乱码当成「卡丢失」。

---

### 3.9 【与 compile 复盘的交叉提醒】

　　本轮 digest 未再踩 compile 的 `batch-XXX-response` 漏体裁问题，但说明 **「文档简写 ≠ 磁盘真名」** 是系统级风险。digest 侧同类风险是：**prompt 里的「approved_by 留 user」与用户说「消化」后的 agent 授权**——skill 已区分，batch 须写对，否则权限语义漂移。

---

## 4. 设计原则汇总（可进 reference / skill 的候选）

1. **落盘前类型闸门**：YAML 解析后的 Python 类型必须符合 schema；冒号字段强制引号。  
2. **自检与写入同一契约**：target / 升格规则 / consumed_buffers 只维护一处。  
3. **Bootstrap 先机制后张力**：空库分波启发式保护 domain + model 优先。  
4. **按结构单元计新建预算**：conflict bundle 例外，避免假「少建卡」。  
5. **enrich 压缩 sources**：追加有上限，超额先归并。  
6. **失败保留 batch**：禁止失败同回合盲目 regenerate。  
7. **auto 闭环含 lint**：子代理加速也不能跳过硬校验。

---

## 5. 建议落地优先级

| 优先级 | 改动 | 消除的问题 |
|---|---|---|
| P0 | `self_check` 校验 sources 元素为 str；报可读错误 | 3.1 |
| P0 | `self_check` 允许 `profile_field` | 3.2 |
| P1 | digest skill / prompt 增加「冒号必须引号」正反例 | 3.1 |
| P1 | bootstrap 分波：meaning-unit 优先 | 3.3 |
| P2 | enrich sources 压缩指引 + warning 文案 | 3.5 |
| P2 | apply 失败保护 batch / 备份 | 3.6 |
| P3 | 新建预算改「结构单元」；construct compact-sources lens | 3.4 / 3.5 |

---

## 6. 本轮已验证的有效做法（保留）

- 用户说「消化」→ `approved_by: agent` 作为本轮写入授权。  
- 空库先 domain，conflict 与两造 claim **同 batch** 写入，避免幽灵 involves。  
- apply 前用短脚本扫描 `sources` 非 str 项。  
- 对依赖未建模型的 tension 显式 skip，并在 operation.note 写明，留待后波（劳动税/拉弗 → Wave02）。  
- 终局用 `digest --plan`「没有待消化的 Buffer」+ Buffer `status: digested` 计数交叉确认。

---

## 7. 终局快照（便于对照）

```text
Buffer: 89 digested / 0 scratch
Cards:  16
  domain×1  市场效率与政策干预
  model×5   竞争市场总剩余最大化、税收无谓损失机制、
            需求价格弹性与总收益判别、供给价格弹性与市场应用、
            价格管制短缺与过剩
  claim×8   税负归宿、最低工资两造、拉弗两造、市场势力与外部性、
            黄牛配置、EITC 补贴助贫
  conflict×2 最低工资助贫与就业代价之争、拉弗曲线减税增收之争
```

　　下一步若做建构，优先处理：domain/sources 膨胀、可能重复的弹性叙述、以及仍挤在 domain「内在张力」里、尚未升格的对立。
