---
name: nexo-emerge
description: >-
  Nexogenesis thinking-body emergence/capture: turn reusable claims, tensions,
  or strong signals into ≤3 candidates, user confirms, then write --batch.
  Use when the user says 记一下, /capture, 沉淀, 涌现, or signal suggests capture.
---

# nexo-emerge（思维体 · 涌现）

## 触发条件

- 用户说「记一下」「/capture」「沉淀」「涌现」；
- `signal --text` 建议捕获。

## 步骤

1. 可选：`python -m nexogenesis signal --text "<触发句>" --root .`
   - 核对可解释触发。
2. 对照 STM（claims_user / tensions / cited_cards）与刚用过的 retrieve 结果。
3. 提出 **≤3** 个候选，每个含：
   - 类型（claim/model/conflict/entity/method/phenomenon）；
   - 一句话内容；
   - 来源/原话锚点；
   - 保存理由；
   - 建议 enrich 的已有 id（若有）。
4. 等用户批准 / 修改 / 驳回。
5. 生成 batch → `python -m nexogenesis write --batch <file>`
   - `approved_by: user`。
6. 写法对齐 `body-structure` + `card-exemplars`。

## 候选类型

- Card：`claim` / `model` / `conflict` / `entity` / `method` / `phenomenon`
- `profile_question`：追加问题清单
- `profile_field`：追加到领域理念/思维模型
- 长期综合可建议 `04-OutBox/discussions/`（nascent，不自动升 Card）

## 纪律

- **捕获永远用户确认**；对话路径禁止 `approved_by: agent`。
- 涌现 ≠ 增产碎片；一事一卡重心。
- 文档观点勿标成用户立场；system 勿擅自 mature / theory active。
- 用户说「先别记」则本会话停止主动涌现提问。

## 必读文档

- `01-Cards/_meta/body-structure.md`
- `01-Cards/_meta/card-exemplars/`
- `AGENTS.md` §5.1（write --batch 事务）
