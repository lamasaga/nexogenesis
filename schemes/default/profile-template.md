# Profile 模板

本项目的 Profile 记录**领域级思考特质**，而非个人语言风格。初始化时会生成三个文件：

- `02-Profile/领域理念.md`：核心立场、价值取向排序、反模式、诚实边界
- `02-Profile/领域思维范式.md`：心智模型、决策启发式、推理模式、默认分析路径、内在张力
- `02-Profile/问题清单.md`：领域待解问题、证据缺口、跨源冲突

`digest`/`construct` 可通过 `write --batch` 的 `target: profile_field` 追加到上述文件。
每条追加须标注来源（Card id 或 Buffer 路径）。
