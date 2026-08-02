---
id: CPI构造与度量偏误
title: CPI构造与度量偏误：固定篮子、三偏误、换算与指数化
type: model
maturity: growing
lifecycle: active
domains:
- 宏观度量与国民收入
origin: document
sources:
- 第25章 生活成本的衡量.md / 25-1 The Consumer Price Index
- 第25章 生活成本的衡量.md / 25-2a Dollar Figures from Different Times
- 第25章 生活成本的衡量.md / 25-2b Indexation
- 第25章 生活成本的衡量.md / Questions for Review
- 第25章 生活成本的衡量.md / Problems and Applications
- 05-Buffer/meaning-unit/2026-08-01-214644-01-复习题锚定：篮子权重、三偏误、进口酒、糖果实际价、名义与实际利率.md
- 05-Buffer/meaning-unit/2026-08-01-214644-01-应用题提炼：CPI偏误配对、鸡蛋工时购买力、社保挂钩与意外通胀债权转移.md
- 05-Buffer/meaning-unit/2026-08-01-214644-01-应用题提炼：Vegopia与球拍饮料算CPI、质量新品种、Voice国平减对比.md
relations:
- target: 宏观度量与国民收入
  type: applies-to
- target: 名义与真实GDP
  type: extends
- target: 名义与实际利率
  type: influences
- target: GDP是福利的良好但不完美度量
  type: influences
created: '2026-08-01'
updated: '2026-08-01'
---

## 核心思想

　　CPI 度量典型消费者篮子成本；通胀率为其百分比变化。固定篮子五步法隔离价格与数量变动，但带来替代/新商品/质量三类向上偏估。跨期用物价比换算名义美元；指数化自动校正合同与部分税制。与 GDP 平减指数通常同向，覆盖与权重不同时可分叉。

## 关键组件

- **构造与权重**：住房约 42% 居首；鸡价涨 10% 对 CPI 影响通常大于鱼子酱——权重大。核心 CPI、PPI 见前。
- **三偏误与配对**：替代（油价涨后多用节油车；电脑降价多买）；新商品（手机发明）；质量（安全气囊；葡萄干增多；瓶容量增大应下调通胀估计）。新口味属品种增加，完美生活成本指数应反映购买力上升。
- **平减对照**：进口酒涨价更影响 CPI；军购只进平减。Voice 国：固定篮 CPI 与当期产出平减可给出不同通胀。
- **换算与实际相对价**：今日金额＝年 T×(今日物价/年 T 物价)。糖条约名义×6、CPI×2 → 相对总体的实际价变为 **3 倍**。鸡蛋工时购买力用「分钟＝蛋价/(时薪/60)」比较。
- **指数化与债权转移**：社保按 CPI 调增；若 CPI 高估且老人篮同总体→生活水平改善；若医疗权重更高须另比。通胀意外偏高→实际利率低于预期，借款人受益、贷款人受损（1970 年代固定利率按揭）。
- **算例操练**：Vegopia/球拍饮料用基年数量加权算 CPI 与通胀率。

## 结构关系或因果链条

　　篮子赋权 → 指数 → 偏误/对照 → 换算与指数化 → 意外通胀再分配债权债务。

## 失效边界

　　习题 stylized；老人专属通胀指数原文未给出完整序列。名义/实际利率决定见利率卡与可贷资金章。

## 原文摘录

> Amount in today’s dollars = Amount in year T dollars × (Price level today / Price level in year T).

> If a price index is computed assuming a fixed basket of goods, it ignores consumer substitution and overstates the increase in the cost of living.

> the GDP deflator reflects the prices of all goods and services produced domestically, while the CPI reflects the prices of all goods and services bought by consumers.
