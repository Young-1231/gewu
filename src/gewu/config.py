"""运行配置：从环境变量 / .env 读取，默认接入 DeepSeek（OpenAI 兼容）。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


@dataclass(frozen=True)
class Settings:
    """全局配置。任何 OpenAI 兼容端点均可：DeepSeek / Qwen / Moonshot / OpenAI / vLLM 等。"""

    api_key: str | None
    base_url: str
    model: str
    temperature: float
    cache_dir: Path
    cache_max_age_days: float
    request_interval: float
    debate_rounds: int

    @classmethod
    def load(cls, **overrides) -> Settings:
        """读取 .env 与环境变量构建配置；overrides 中的非 None 值优先。

        API key 查找顺序：GEWU_API_KEY > DEEPSEEK_API_KEY > OPENAI_API_KEY。
        """
        load_dotenv()

        def pick(*names: str, default: str | None = None) -> str | None:
            for name in names:
                value = os.environ.get(name)
                if value:
                    return value
            return default

        values: dict = {
            "api_key": pick("GEWU_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY"),
            "base_url": pick("GEWU_BASE_URL", default=DEFAULT_BASE_URL),
            "model": pick("GEWU_MODEL", default=DEFAULT_MODEL),
            "temperature": float(pick("GEWU_TEMPERATURE", default="0.3")),
            "cache_dir": Path(pick("GEWU_CACHE_DIR", default=str(Path.home() / ".gewu" / "cache"))),
            "cache_max_age_days": float(pick("GEWU_CACHE_MAX_AGE_DAYS", default="1")),
            "request_interval": float(pick("GEWU_REQUEST_INTERVAL", default="1.0")),
            "debate_rounds": int(pick("GEWU_DEBATE_ROUNDS", default="2")),
        }
        values.update({k: v for k, v in overrides.items() if v is not None})
        # expanduser：.env 中常见 GEWU_CACHE_DIR=~/.gewu/cache 写法，不展开会在 cwd 建出字面 "~" 目录
        values["cache_dir"] = Path(values["cache_dir"]).expanduser()
        return cls(**values)
