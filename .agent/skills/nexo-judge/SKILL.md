---
name: nexo-judge
description: >-
  Nexogenesis thinking-body judgment under risk: retrieve --mode judge, 2–4
  relevant lenses, strongest counterexample, locate don't verdict truth. Use for
  重要决策, 明显争议, 跨域因果, /judge, or when the user asks for deep judgment.
---

# nexo-judge（思维体 · 判断）

## 触发条件

- 重要决策、明显争议、跨域因果；
- 用户明确要求深入判断。

## 步骤

1. `python -m nexogenesis retrieve --query "…" --mode judge --root .`
   - 可加 `--seed <card_id>` 聚焦。
2. 读取 Context Package 与 `02-Profile/领域理念.md`、`02-Profile/领域思维模型.md`。
3. 从相关角度中选 **2–4** 个真正有用的透镜
   - 如：组成/机制/证据/演变/反例/行动等；
   - **不强制六透镜全做**，无助于问题的跳过。
4. 回答结构：
   - 直接判断 →
   - 依据（标归因）→
   - 最强反例/限制 →
   - 可选行动代价。
5. 分析默认留对话；仅当有长期复用价值时建议 `04-OutBox/discussions/`。
6. 若凝结出可维护主张 → 建议转 `nexo-emerge`（仍须用户确认）。

## 纪律

- 区分事实 / 因果 / 价值；事实错误不能包装成「另一视角」。
- 不模仿用户口吻冒充其信念。
- system 升格 theory active 须用户批。
- 定位非裁决：解释什么、何处失效、生成什么，不宣布绝对真假。

## 必读文档

- `AGENTS.md` §4.1、§4.4
- `02-Profile/领域理念.md`
- `02-Profile/领域思维模型.md`
