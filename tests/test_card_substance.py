from nexogenesis.body_slots import buffer_substance_warnings, card_substance_warnings


def test_substance_flags_title_echo_and_hollow_evidence():
    warns = card_substance_warnings(
        card_id="第二库存研究或与周期之轮衔接",
        title="第二库存研究或与周期之轮衔接",
        card_type="claim",
        body=(
            "## 一句话主张\n\n"
            "　　第二库存研究或与周期之轮衔接\n\n"
            "## 依据\n\n"
            "　　原文未提及：具体依据。\n\n"
            "## 已知限制\n\n"
            "　　关联假设，证据待检验。\n\n"
            "## 原文摘录\n\n"
            "　　原文未提及：摘录。\n"
        ),
    )
    blob = " ".join(warns)
    assert "复读标题" in blob or "回声" in blob
    assert "空洞" in blob or "link-hypothesis" in blob


def test_substance_flags_chart_phenomenon():
    warns = card_substance_warnings(
        card_id="表9商品产能周期",
        title="表9：商品产能周期不同阶段收益率",
        card_type="phenomenon",
        body=(
            "## 模式描述\n\n"
            "　　表9：商品产能周期不同阶段收益率\n\n"
            "## 典型实例\n\n"
            "　　| a | b |\n\n"
            "## 反例与失效条件\n\n"
            "　　图表质料，宜并入相关模型/主张之依据。\n\n"
            "## 原文摘录\n\n"
            "　　原文未提及：摘录。\n"
        ),
    )
    assert any("图表类" in w or "不宜作独立" in w for w in warns)


def test_good_claim_passes_substance():
    warns = card_substance_warnings(
        card_id="美元升值与中国去泡沫共振",
        title="美元升值与中国去泡沫共振将加速资产价格下行",
        card_type="claim",
        body=(
            "## 一句话主张\n\n"
            "　　美元大幅升值历史上冲击拉美与日本；对中国，若与增长中枢下移的去泡沫过程共振，"
            "长时间较大幅度升值可能加速泡沫破灭。\n\n"
            "## 依据\n\n"
            "　　与 2012 以来第三轮美元牛市及 2015 资产安全化叙事跨源对照。\n\n"
            "## 已知限制\n\n"
            "　　共振的量化触发条件未给出。\n\n"
            "## 原文摘录\n\n"
            "　　「如果美元升值与中国去泡沫过程共振……」——美元破百\n"
        ),
    )
    assert warns == []


def test_buffer_substance_flags_hollow_meaning_unit():
    warns = buffer_substance_warnings(
        role="meaning-unit",
        title="第二库存或与周期之轮衔接",
        body=(
            "### 核心表达\n\n"
            "　　第二库存或与周期之轮衔接\n\n"
            "### 依据与细节\n\n"
            "　　原文未提及：具体依据。\n\n"
            "### 限制与边界\n\n"
            "　　待检验。\n\n"
            "### 原文摘录\n\n"
            "　　原文未提及：摘录。\n"
        ),
    )
    blob = " ".join(warns)
    assert "复读" in blob or "link-hypothesis" in blob
    assert "空洞" in blob or "空壳" in blob


def test_compile_format_rules_favor_fast_slices():
    from nexogenesis.ingest.prompts import format_rules

    text = format_rules()
    assert "意义切片" in text or "快节奏" in text
    assert "title" in text and "source" in text
    assert "不要求" in text or "四级" in text or "自由" in text
    assert "预售" in text or "滋养" in text or "骨架" in text
    assert "各自独立成块" not in text
    assert "proposed_card_type" in text  # 明确不要写
    assert "created" in text  # 说明由 Harness 补