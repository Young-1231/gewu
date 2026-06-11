"""DataBundle：一次研究任务的全部 Point-in-Time 数据快照。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd


@dataclass
class DataBundle:
    """在 ``as_of`` 时点可见的全部数据。agent 只能通过它接触世界。"""

    symbol: str
    market: str  # "ashare" | "us"
    as_of: date
    name: str
    profile: dict
    daily: pd.DataFrame  # PIT 截断 + 技术指标列
    financial_indicators: pd.DataFrame | None = None
    financial_abstract: pd.DataFrame | None = None
    valuation: pd.DataFrame | None = None
    news: pd.DataFrame | None = None
    technical_summary: dict = field(default_factory=dict)
    fundamental_summary: dict = field(default_factory=dict)
    valuation_summary: dict = field(default_factory=dict)
    sources: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
