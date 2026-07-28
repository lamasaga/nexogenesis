"""思维体：注意力配置、短期记忆、Working Set、强信号。"""

from nexogenesis.thinking.config import load_attention_config, resolve_effective_config
from nexogenesis.thinking.stm import STMStore

__all__ = [
    "load_attention_config",
    "resolve_effective_config",
    "STMStore",
]
