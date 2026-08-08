"""重新生成演示知识库 demo-kb/01-Cards（分发演示与开发调试的种子数据）。

用法：python demo-kb/gen_demo_kb.py
"""
import random
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
CARDS = ROOT / "01-Cards"

DOMAINS = {
    "spec-psych": "投机心理",
    "mkt-struct": "市场结构",
    "paradigm": "思想范式",
    "risk-disc": "风险纪律",
    "narrative": "叙事传播",
    "method": "方法论",
}

# (id, title, type, domain, [(target, relation_type)])
CARDS_SPEC = [
    ("hope-fear", "希望与恐惧是投机者的内在敌人", "claim", "spec-psych",
     [("reflexivity", "supports"), ("stop-loss", "applies-to")]),
    ("crowd-polar", "市场群体极化", "phenomenon", "spec-psych",
     [("hope-fear", "supports"), ("narrative-econ", "influences")]),
    ("noise-trader", "噪声交易者", "entity", "spec-psych",
     [("crowd-polar", "supports")]),
    ("herd-cascade", "羊群级联的非线性拐点", "model", "spec-psych",
     [("crowd-polar", "extends"), ("liquidity-spiral", "supports")]),
    ("overconfidence", "过度自信的校准失灵", "claim", "spec-psych",
     [("stop-loss", "conflicts-with")]),
    ("liq-spiral", "流动性螺旋", "model", "mkt-struct",
     [("crowd-polar", "supports"), ("stop-loss", "applies-to")]),
    ("mkt-micro", "市场微观结构的订单流毒性", "model", "mkt-struct",
     [("liq-spiral", "supports")]),
    ("liquidity-spiral", "流动性螺旋的自我强化", "claim", "mkt-struct",
     [("liq-spiral", "extends")]),
    ("vol-cluster", "波动率聚集现象", "phenomenon", "mkt-struct",
     [("liq-spiral", "supports")]),
    ("reflexivity", "反身性反馈环", "model", "paradigm",
     [("narrative-econ", "supports"), ("hope-fear", "supports")]),
    ("paradigm-shift", "范式转移", "model", "paradigm",
     [("reflexivity", "extends")]),
    ("narrative-econ", "叙事经济学", "model", "paradigm",
     [("crowd-polar", "influences")]),
    ("emh-limit", "有效市场假说的边界", "claim", "paradigm",
     [("reflexivity", "conflicts-with")]),
    ("stop-loss", "先例失效即止损", "method", "risk-disc",
     [("hope-fear", "applies-to"), ("safety-margin", "supports")]),
    ("safety-margin", "安全边际", "model", "risk-disc",
     [("stop-loss", "supports")]),
    ("position-sizing", "凯利准则与仓位管理", "method", "risk-disc",
     [("safety-margin", "based-on")]),
    ("tail-hedge", "尾部对冲的成本悖论", "conflict", "risk-disc",
     [("stop-loss", "involves"), ("position-sizing", "involves")]),
    ("narrative-cascade", "叙事级联的传播阈值", "model", "narrative",
     [("narrative-econ", "extends"), ("crowd-polar", "supports")]),
    ("meme-stock", "模因股事件", "phenomenon", "narrative",
     [("narrative-cascade", "example-of")]),
    ("info-cascade", "信息瀑布与反转", "model", "narrative",
     [("narrative-cascade", "conflicts-with")]),
    ("checklist", "决策清单法", "method", "method",
     [("stop-loss", "supports")]),
    ("journal-review", "交易日志复盘机制", "method", "method",
     [("checklist", "extends")]),
    ("base-rate", "基础概率忽视", "phenomenon", "method",
     [("overconfidence", "supports")]),
]


def main() -> None:
    random.seed(7)
    CARDS.mkdir(parents=True, exist_ok=True)
    for did, dtitle in DOMAINS.items():
        _write(did, dtitle, "domain", [did], [])
    for cid, title, ctype, domain, rels in CARDS_SPEC:
        _write(cid, title, ctype, [domain],
               [{"target": t, "type": r, "note": ""} for t, r in rels])
    print(f"demo kb: {len(DOMAINS) + len(CARDS_SPEC)} cards -> {CARDS}")


def _write(cid: str, title: str, type_: str, domains: list, relations: list) -> None:
    meta = {
        "id": cid, "title": title, "type": type_,
        "maturity": "growing", "lifecycle": "active",
        "domains": domains, "origin": "user", "sources": ["demo"],
        "relations": relations,
        "created": "2026-08-08", "updated": "2026-08-08",
    }
    body = f"{title}。这是演示用占位正文，用于截图走查时验证卡片阅读器与图谱标注。"
    text = "---\n" + yaml.safe_dump(meta, allow_unicode=True) + f"---\n\n{body}\n"
    (CARDS / f"{cid}.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
