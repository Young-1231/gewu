"""历史指数成分股票池（baostock）：防幸存者偏差的关键。

baostock 的 ``query_hs300_stocks(date)`` 支持按历史日期返回当时的
沪深300成分（含此后退市/调出的股票），这是免费数据源中少有的能力
（见 docs/research/supplement-data-sources.md）。
"""

from __future__ import annotations

import logging
import random
from datetime import date

logger = logging.getLogger(__name__)


def csi300_members(as_of: date) -> list[str]:
    """as_of 当日的沪深300成分股代码（6位数字）。需要网络，登录免费匿名账户。"""
    import baostock as bs

    login = bs.login()
    if login.error_code != "0":
        raise RuntimeError(f"baostock 登录失败: {login.error_msg}")
    try:
        rs = bs.query_hs300_stocks(date=str(as_of))
        if rs.error_code != "0":
            raise RuntimeError(f"查询沪深300历史成分失败: {rs.error_msg}")
        symbols = []
        while rs.next():
            row = rs.get_row_data()  # [updateDate, code(sh.600519), code_name]
            symbols.append(row[1].split(".")[-1])
        return symbols
    finally:
        bs.logout()


def sample_universe(symbols: list[str], size: int, seed: int = 42) -> list[str]:
    """可复现实验抽样：固定 seed，避免"挑表现好的股票"这类数据窥探。"""
    if size >= len(symbols):
        return sorted(symbols)
    rng = random.Random(seed)
    return sorted(rng.sample(symbols, size))
