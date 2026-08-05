---
name: nexo-judge
description: |
  Nexogenesis 深判：对复杂问题、冲突或决策进行多透镜分析，定位而非裁决。
  当用户说「深判」「/judge」「怎么判断」「评估一下」或要求多视角分析时触发。
compatibility: Nexogenesis 项目，已初始化 .agent/reference/ 与 02-Profile/
---

# Grounding（按顺序必读）

1. `.agent/reference/constraint-layers.md` — 约束分层与权限。
2. `.agent/reference/retrieval-design.md` — 双轨检索，尤其 judge 模式。
3. `.agent/reference/thinking-body.md` — 思维体注意力与会话纪律。
4. `02-Profile/领域理念.md` — 价值取向与反模式。
5. `02-Profile/领域思维范式.md` — 决策启发式与透镜。

# Workflows

> 完整 CLI 参数见 [`.agent/reference/harness-cli.md`](.agent/reference/harness-cli.md)；以下只列出本 skill 的典型调用顺序。

1. 明确判断对象与用户关心的维度。
2. 执行检索：
   ```bash
   python -m nexogenesis retrieve --query "<判断对象>" --mode judge --root .
   ```
3. 选择 2–4 个透镜（如：证据强度、适用边界、学派立场、反事实、长期后果）。
4. 对每个透镜：
   - 说明该透镜关注什么；
   - 从 Context Package 中提取相关卡片/质料；
   - 给出定位：哪些证据支持、哪些削弱、哪些仍不确定。
5. 综合：不替用户裁决，而是给出「若接受 A，则需承担 X；若接受 B，则需解释 Y」的结构性结论。
6. 若涌现值得追踪的问题，追加到 `02-Profile/问题清单.md`（经用户确认后通过 write --batch）。

# Invariants

- 深判是「定位」不是「裁决」；最终判断权留给用户。
- 必须显式区分事实、推断与价值判断。
- 使用 `conflict` 卡和 `relations` 显化对立，而非模糊调和。
- 所有引用必须可追溯到 Card id 或 Buffer 路径。
- 每个透镜用一段连贯叙述，不堆子弹列表；综合前自检：删去所有卡片 id 与英文缩写后，用户是否仍能复述结论依据？不能则重写。

# Anti-patterns

- 用平均化结论回避张力。
- 不读 Context 就给出判断。
- 把推断包装成事实。
- 自动把判断结论写成 `claim` 卡。
- 用术语串代替推理过程；评判过早收束成口号。
