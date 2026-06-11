"""Point-in-Time 可见性规则：在 as_of 日期下，哪些财报数据"依法已经披露"。

没有公告日数据时，采用**法定披露截止日**作为可见日期——这是最保守的近似：
可能晚于真实公告日（漏掉已披露的数据），但绝不会把未来数据泄漏给过去。
A股法定披露截止日（《上市公司信息披露管理办法》）：
- 一季报（03-31 期末）：当年 04-30
- 半年报（06-30 期末）：当年 08-31
- 三季报（09-30 期末）：当年 10-31
- 年报（12-31 期末）：次年 04-30
"""

from __future__ import annotations

from datetime import date

import pandas as pd


def report_visible_date(period_end: date) -> date:
    """法定披露截止日；非标准期末（极少见）按期末 + 120 天兜底。"""
    month_day = (period_end.month, period_end.day)
    if month_day == (3, 31):
        return date(period_end.year, 4, 30)
    if month_day == (6, 30):
        return date(period_end.year, 8, 31)
    if month_day == (9, 30):
        return date(period_end.year, 10, 31)
    if month_day == (12, 31):
        return date(period_end.year + 1, 4, 30)
    return period_end + pd.Timedelta(days=120).to_pytimedelta()


def filter_periods_pit(periods: pd.Series, as_of: date) -> pd.Series:
    """对报告期末序列返回布尔掩码：该期财报在 as_of 时点是否已（依法）可见。"""
    ends = pd.to_datetime(periods, errors="coerce")
    visible = ends.map(
        lambda ts: report_visible_date(ts.date()) <= as_of if pd.notna(ts) else False
    )
    return visible.astype(bool)
