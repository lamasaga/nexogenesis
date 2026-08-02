---
id: 名义与真实GDP
title: 名义与真实GDP：现价、基年不变价与产量度量
type: model
maturity: growing
lifecycle: active
domains:
- 宏观度量与国民收入
origin: document
sources:
- 第24章 一国收入的衡量.md / 24-4 Real versus Nominal GDP / 24-4a
- 第24章 一国收入的衡量.md / 24-4a A Numerical Example
- 第24章 一国收入的衡量.md / 24-4b The GDP Deflator
- 第24章 一国收入的衡量.md / 24-4b A Half Century of Real GDP
- 第24章 一国收入的衡量.md / Problems and Applications
- 第25章 生活成本的衡量.md / 25-1c The GDP Deflator versus the Consumer Price Index
- 05-Buffer/meaning-unit/2026-08-01-205510-01-名义GDP用现价；真实GDP用基年不变价分离产量与物价.md
- 05-Buffer/meaning-unit/2026-08-01-205515-01-GDP平减指数=名义GDP真实GDP×100，只反映物价.md
- 05-Buffer/meaning-unit/2026-08-01-214536-01-GDP平减指数vs-CPI：国内生产-vs-消费者购买；固定篮子-vs-当期产出篮子.md
relations:
- target: 宏观度量与国民收入
  type: applies-to
- target: GDP支出法定义与边界
  type: based-on
- target: GDP支出四分法恒等式
  type: extends
- target: GDP是福利的良好但不完美度量
  type: supports
  note: 真实/人均口径支撑跨期跨国福祉比较，但不消除遗漏
- target: CPI构造与度量偏误
  type: influences
  note: 平减指数与 CPI 对照：国内生产篮子 vs 消费者固定篮子
created: '2026-08-01'
updated: '2026-08-01'
---

## 核心思想

　　名义 GDP 用现价估价生产（混杂产量与物价）；真实 GDP 用不变基年价格，只反映产量。由二者之比得 GDP 平减指数，只反映物价；其百分比变化即用平减指数度量的通胀率。半世纪美国真实 GDP 约增四倍，但增长被衰退间歇打断。经济学家说「GDP」通常指真实 GDP，「增长」指真实 GDP 百分比变化。晚间新闻更常报基于 CPI 的通胀；平减指数与 CPI 通常同向，但覆盖与权重规则不同（详见 CPI 卡）。

## 关键组件

- **名义 vs 真实**：名义用当前价格；真实回答「若用基年价格为今年产出估价，价值多少」。物价变动不影响真实 GDP。
- **热狗汉堡算例（基年 2022）**：名义 $200→$600→$1,200；真实 $200→$350→$500。真实上升归因于产量。
- **GDP 平减指数**：deflator = (名义/真实)×100。基年恒为 100。产量升价不变→平减不变；价升产量不变→平减上升。热狗例：100、171、240。
- **通胀率**：[(平减₂−平减₁)/平减₁]×100。算例 100→171 为 **71%**；171→240 为 **40%**。平减指数之名来自把通胀从名义 GDP 中「打出去」。
- **与 CPI 对照**：平减覆盖国内生产全部；CPI 覆盖消费者购买。军购涨价只进平减；进口消费品涨价进 CPI。平减用当期产出权重，CPI 用固定篮子。1965 以来大体同向；油价剧烈变动时分叉更显。
- **半世纪真实 GDP**：2021 年约为 1970 年约四倍（约 3%/年）；上行偶被衰退打断。旧经验法则：连续两季真实 GDP 下降；2020 疫情例外——大幅下跌但仅一季。长期增长与短期波动需不同模型。
- **速测**：饼干 10@$2→12@$3（基年第1年）真实升 **20%**；产量全升 5%、价格全降 5% → 真实升 5%、名义大致不变。
- **应用恒等操练**：知名义/真实/平减任二可求其三。牛奶蜂蜜例：2024 产量翻倍价不变→名义真实皆升、平减不变；2025 价翻倍产量不变→名义与平减升、真实不变。

## 结构关系或因果链条

　　市价加总→名义 → 基年重估→真实 → 名义/真实→平减 → 平减变化→通胀率 → 跨期「增长」读真实；与 CPI 并列时按问题选度量（产出物价 vs 生活成本）。

## 失效边界

　　基年选择与质量变化未穷尽。CPI 的替代/新商品/质量偏误与指数化政策争议见「CPI构造与度量偏误」。真实 GDP 仍非完备福利指数（见福祉主张卡）。衰退官方判定无单一铁律。

## 原文摘录

> Nominal GDP uses current prices to value the economy’s production of goods and services. Real GDP uses constant base-year prices to value the economy’s production.

> The GDP deflator is a measure of the price level calculated as the ratio of nominal GDP to real GDP times 100.

> The real GDP of the U.S. economy in 2021 was about four times its 1970 level. … growth is not steady.

> the GDP deflator reflects the prices of all goods and services produced domestically, while the CPI reflects the prices of all goods and services bought by consumers.
