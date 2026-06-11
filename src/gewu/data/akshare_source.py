"""A股数据源适配：基于 akshare 的多源降级抓取，统一输出标准 schema。

降级顺序的依据（2026-06 实测）：东财 push2 行情接口在部分网络环境直接拒绝连接，
而新浪/腾讯日线、东财数据中心（datacenter-web）、巨潮概况均稳定可用。
因此行情按 东财 → 新浪 → 腾讯 依次尝试，任一成功即返回。
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

import pandas as pd

# pandas 3 在安装 pyarrow 后默认用 Arrow(RE2) 字符串引擎，而 akshare 内部正则
# 含 RE2 不支持的 \u 转义（实测 stock_news_em 抛 ArrowInvalid），强制回退 Python 引擎。
pd.set_option("mode.string_storage", "python")

import akshare as ak  # noqa: E402

from gewu.data.cache import SOURCE_ATTR  # noqa: E402

logger = logging.getLogger(__name__)

_DAILY_COLUMNS = ["date", "open", "high", "low", "close", "volume"]

_last_request_ts = 0.0


def _throttle(interval: float) -> None:
    """模块级节流：任意两次上游请求（含成功路径、跨数据集）至少间隔 interval 秒。"""
    global _last_request_ts
    wait = _last_request_ts + interval - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_request_ts = time.monotonic()


def _exchange_prefix(symbol: str) -> str:
    if symbol.startswith("6"):
        return "sh"
    if symbol.startswith(("4", "8")):
        return "bj"
    return "sz"


def _try_sources(
    dataset: str,
    candidates: list[tuple[str, Callable[[], pd.DataFrame]]],
    request_interval: float = 1.0,
) -> pd.DataFrame:
    """依序尝试多个数据源，返回首个非空结果；全部失败则抛出汇总异常。"""
    errors: list[str] = []
    for name, fn in candidates:
        _throttle(request_interval)
        try:
            df = fn()
            if df is not None and not df.empty:
                df.attrs[SOURCE_ATTR] = name
                return df
            errors.append(f"{name}: 返回空数据")
        except Exception as error:
            errors.append(f"{name}: {type(error).__name__}: {error}")
            logger.debug("数据源 %s/%s 失败: %s", dataset, name, error)
    raise RuntimeError(f"{dataset} 全部数据源失败 → " + " | ".join(errors))


def fetch_daily(symbol: str, request_interval: float = 1.0) -> pd.DataFrame:
    """前复权日线，标准列：date/open/high/low/close/volume。

    注意：各源成交量单位不同（东财:手，新浪:股，腾讯:手），
    单源内部一致，量比等相对指标不受影响；跨源绝对值不可比。
    """
    prefixed = f"{_exchange_prefix(symbol)}{symbol}"

    def from_eastmoney() -> pd.DataFrame:
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
        return df.rename(
            columns={"日期": "date", "开盘": "open", "最高": "high", "最低": "low", "收盘": "close", "成交量": "volume"}
        )

    def from_sina() -> pd.DataFrame:
        return ak.stock_zh_a_daily(symbol=prefixed, adjust="qfq")

    def from_tencent() -> pd.DataFrame:
        df = ak.stock_zh_a_hist_tx(symbol=prefixed)
        return df.rename(columns={"amount": "volume"})

    df = _try_sources(
        "daily",
        [("eastmoney", from_eastmoney), ("sina", from_sina), ("tencent", from_tencent)],
        request_interval,
    )
    if "date" not in df.columns:
        df = df.reset_index()
    df["date"] = pd.to_datetime(df["date"])
    keep = [c for c in _DAILY_COLUMNS if c in df.columns]
    out = df[keep].sort_values("date").reset_index(drop=True)
    out.attrs[SOURCE_ATTR] = df.attrs.get(SOURCE_ATTR, "unknown")
    return out


def fetch_financial_indicators(
    symbol: str, start_year: str = "2019", request_interval: float = 1.0
) -> pd.DataFrame:
    """财务分析指标（新浪），按报告期一行，含营收/利润增速、ROE、毛利率、负债率等。"""

    def from_sina() -> pd.DataFrame:
        df = ak.stock_financial_analysis_indicator(symbol=symbol, start_year=start_year)
        df["日期"] = pd.to_datetime(df["日期"])
        return df.sort_values("日期").reset_index(drop=True)

    return _try_sources("financial_indicators", [("sina", from_sina)], request_interval)


def fetch_financial_abstract(symbol: str, request_interval: float = 1.0) -> pd.DataFrame:
    """财务摘要（同花顺口径，via akshare）：行=指标，列=报告期（YYYYMMDD）。"""

    def from_ths() -> pd.DataFrame:
        return ak.stock_financial_abstract(symbol=symbol)

    return _try_sources("financial_abstract", [("ths", from_ths)], request_interval)


def fetch_valuation(symbol: str, request_interval: float = 1.0) -> pd.DataFrame:
    """估值日频序列，标准列：date/pe_ttm/pb/total_mv（元）。

    主源东财数据中心（全字段）；降级百度股市通（仅 PE-TTM）。
    """

    def from_eastmoney() -> pd.DataFrame:
        df = ak.stock_value_em(symbol=symbol)
        df = df.rename(
            columns={"数据日期": "date", "PE(TTM)": "pe_ttm", "市净率": "pb", "总市值": "total_mv"}
        )
        return df[["date", "pe_ttm", "pb", "total_mv"]]

    def from_baidu() -> pd.DataFrame:
        df = ak.stock_zh_valuation_baidu(symbol=symbol, indicator="市盈率(TTM)", period="近五年")
        return df.rename(columns={"value": "pe_ttm"})

    df = _try_sources(
        "valuation", [("eastmoney", from_eastmoney), ("baidu", from_baidu)], request_interval
    )
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def fetch_news(symbol: str, request_interval: float = 1.0) -> pd.DataFrame:
    """个股新闻（东财搜索接口，近期约百条），标准列：发布时间/新闻标题/新闻内容/文章来源/新闻链接。"""

    def from_eastmoney() -> pd.DataFrame:
        df = ak.stock_news_em(symbol=symbol)
        df["发布时间"] = pd.to_datetime(df["发布时间"])
        return df.sort_values("发布时间").reset_index(drop=True)

    return _try_sources("news", [("eastmoney_news", from_eastmoney)], request_interval)


def fetch_profile(symbol: str, request_interval: float = 1.0) -> pd.DataFrame:
    """公司概况：主源巨潮资讯（机构全景），东财个股信息作为补充（部分网络不可用）。"""

    def from_cninfo() -> pd.DataFrame:
        return ak.stock_profile_cninfo(symbol=symbol)

    def from_eastmoney() -> pd.DataFrame:
        df = ak.stock_individual_info_em(symbol=symbol)
        return df.set_index("item").T.reset_index(drop=True)

    return _try_sources(
        "profile", [("cninfo", from_cninfo), ("eastmoney", from_eastmoney)], request_interval
    )
