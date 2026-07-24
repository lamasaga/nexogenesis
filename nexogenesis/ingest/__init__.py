"""文档摄入引擎公共常量与工具函数。"""

import re
from pathlib import Path

DEFAULT_BATCH_LIMIT = 30000

WORD_RE = re.compile(r"[a-zA-Z]+(?:['-][a-zA-Z]+)?")

CHINESE_CHAR_COST_NUM = 2
ENGLISH_WORD_COST_NUM = 3


def count_chars(text: str) -> int:
    """估算等效中文字符数。

    - 中文字符：+1
    - 英文单词：+1.5（向上取整）
    - 数字、标点、空白：忽略
    """
    chinese = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    english_words = len(WORD_RE.findall(text))
    return (chinese * CHINESE_CHAR_COST_NUM + english_words * ENGLISH_WORD_COST_NUM + 1) // 2


VALID_BUFFER_TYPES = {
    "domain",
    "claim",
    "phenomenon",
    "model",
    "method",
    "entity",
    "conflict",
}


def ensure_buffer_dirs(buffer_dir: Path) -> None:
    """确保 Buffer 子目录存在（7 种类型）。"""
    for subtype in VALID_BUFFER_TYPES:
        (buffer_dir / subtype).mkdir(parents=True, exist_ok=True)
