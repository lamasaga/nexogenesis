---
id: OLS与自然实验识别路径
title: OLS与自然实验识别路径：估参、不确定性、混淆控制与IV
type: method
maturity: growing
lifecycle: active
domains:
- 微观分析基础
origin: document
sources:
- 第38章 附录：经济学家如何使用数据.md / 38-3a Finding the Best Estimate
- 第38章 附录：经济学家如何使用数据.md / 38-3b Gauging Uncertainty
- 第38章 附录：经济学家如何使用数据.md / 38-3c Accounting for Confounding Variables
- 第38章 附录：经济学家如何使用数据.md / 38-3d Establishing Causal Effects
- 第38章 附录：经济学家如何使用数据.md / Chapter in a Nutshell
- 05-Buffer/meaning-unit/2026-08-02-031214-01-从定性到定量：线性回归与OLS估计多上一年学涨薪多少.md
- 05-Buffer/meaning-unit/2026-08-02-031214-01-抽样变异与标准误：估计精度随样本量上升而收窄.md
- 05-Buffer/meaning-unit/2026-08-02-031220-01-多元回归：把IQ纳入模型后学龄工资回报从3.16降到1.86.md
- 05-Buffer/meaning-unit/2026-08-02-031220-01-自然实验与工具变量：用类随机冲击识别因果效应.md
- 05-Buffer/meaning-unit/2026-08-02-031220-01-越南征兵抽签：Angrist用工具变量估军人身份压低平民收入约15%.md
- 05-Buffer/meaning-unit/2026-08-02-031310-01-Ellie研究-vignette：从截面OLS到自然实验工具变量的完整识别链.md
- 05-Buffer/meaning-unit/2026-08-02-031235-01-复习题锚定：实验观察分野、OLS标准误、混淆两解与数据结构.md
relations:
- target: 微观分析基础
  type: applies-to
- target: 因果识别陷阱
  type: based-on
  note: 本路径是陷阱清单的操作化解法
- target: 经济数据分析四目标
  type: applies-to
  note: 服务估参、检验假说与预测目标的技术阶梯
- target: 人力资本与信号论之争
  type: applies-to
  note: 学龄工资回报估计是教育溢价经验裁定的标准路径
- target: 实证分析与规范判断之分
  type: applies-to
created: '2026-08-02'
updated: '2026-08-02'
---

## 输入

　　截面或观察数据上的定性理论主张（如「教育抬工资」「服役影响平民收入」「人口增长影响人均收入」）；关注自变量与因变量；可疑混淆变量清单；以及可选的类随机冲击（自然实验/工具变量候选）。

## 步骤

1. **从定性到线性回归**：把「教育提高生产率从而抬工资」落成可估模型 WAGE_i = b0 + b1×SCHOOL_i + ε_i。b1 是关注参数（每多一年学涨多少工资）；ε 代表经验与认知能力等未入模力量，并假定残差均值约为零且与自变量不相关。散点常呈云状正相关而非贴合直线——教育只是工资决定因素之一。
2. **OLS 找最佳拟合**：普通最小二乘选使残差平方和最小的参数。七人示意截面得 WAGE = −10.7 + 3.16×SCHOOL，即每多一年学约涨 3.16 美元/时。一般路径：找相关数据 → 设定统计模型 → OLS 估参 → 定量结论。
3. **用标准误量不确定性**：抽样变异使不同随机样本给出略不同估计。标准误 = 衡量因抽样变异带来的参数估计不确定性；经验法则：真值约有 95% 概率落在估计值 ± 两倍标准误（误差幅度）。七点样本 b1 标准误 1.35，95% 区间约 0.46–5.86，很宽；样本扩到约 700 点则标准误约 0.135，区间收窄到约 2.89–3.43。估计随更大样本更精确。
4. **多元回归控制混淆**：若能力更高者读更多书，残差（含能力）与学龄正相关，简单 OLS 的 b1 向上偏误。测量混淆变量后扩展为 WAGE = b0 + b1×SCHOOL + b2×IQ + ε；控制 IQ 后学龄效应从 3.16 降至 1.86 美元/时。省略变量若直接影响因变量且与自变量相关，OLS 会混淆二者；纳入多元回归是解法之一。
5. **自然实验与工具变量**：当混淆难测或存在反向因果时，寻找机会事件使变异类似 RCT。工具须（1）与关注自变量相关；（2）除通过该自变量外不影响因变量。Phyllis 突袭付学费例：处理/对照校学龄差 2.7 年、工资差 5 美元 → 约 1.85 美元/年。须追问「是否真如看似随机」。
6. **Angrist 征兵抽签**：直接比退伍/非退伍收入有选择偏误。1970 年代初越南征兵签号近乎随机强制——签号影响服役、除经服役外不影响后续收入，是理想工具。结论：1980 年代初白人退伍军人收入约比可比非退伍军人低 15%。2021 年 Angrist 因因果方法论获诺贝尔奖。
7. **Ellie 识别链（操作检查单）**：50 国截面 → OLS 负相关且标准误小 → 承认观察数据 → 教育作混淆加入多元回归 → 担心收入→避孕→人口的反向因果 → 联合国随机推广避孕作自然实验 → IV 估人口增长对收入的因果效应。复习锚：混淆两解＝多元回归纳入 + 自然实验/IV。

## 输出

　　参数点估计与标准误（或置信区间）；是否已控制关键混淆；若声称因果，须标明自然实验/IV 来源及其「类随机」保留条件；明确本附录仅为旋风导览，完整工具箱需另修计量课。

## 适用边界

　　OLS 无偏依赖残差与自变量不相关——观察数据上常被违背。多元回归只能控制**已测量**的混淆。自然实验外生性可被学校财富差、慈善家选择性要约等污染。IV 弱工具与排他限制失败会使估计崩溃。不覆盖 DID/RDD/完整渐近理论。

## 原文摘录

> According to the estimated model, each year of schooling increases a worker’s wage by $3.16 per hour.

> Estimated parameters become more precise with larger samples.

> As we expected, once we control for IQ, the estimated effect of schooling decreases.

> A natural experiment is a chance event that generates variation in the data as if a randomized controlled trial had been conducted.

> In the early 1980s … the earnings of white veterans were approximately 15 percent less than the earnings of comparable nonveterans.

> Explain the problem of confounding variables, and describe two methods for solving the problem.
