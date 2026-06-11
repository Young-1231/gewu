"""美股数据源适配（兼容层）：yfinance。

注意：Yahoo 自 2025 年起对未认证流量限流较严（429 频发），本层依赖缓存与
重试缓解；美股为本项目的"兼容"档而非主战场，深度数据（如估值历史分位）
留待 SEC EDGAR 集成（见 docs/research/supplement-data-sources.md）。
"""

from __future__ import annotations

import logging

import pandas as pd
import yfinance as yf

from gewu.data.cache import SOURCE_ATTR

logger = logging.getLogger(__name__)


def fetch_daily(symbol: str) -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="5y", auto_adjust=True)
    if df.empty:
        raise RuntimeError(f"yfinance 未返回 {symbol} 的行情（可能被限流或代码无效）")
    df = df.reset_index().rename(
        columns={"Date": "date", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    )
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    out = df[["date", "open", "high", "low", "close", "volume"]].sort_values("date").reset_index(drop=True)
    out.attrs[SOURCE_ATTR] = "yfinance"
    return out


def fetch_profile(symbol: str) -> pd.DataFrame:
    info = yf.Ticker(symbol).info or {}
    keep = {
        "公司名称": info.get("longName") or info.get("shortName") or symbol,
        "行业": info.get("industry"),
        "板块": info.get("sector"),
        "总市值": info.get("marketCap"),
        "PE(TTM)": info.get("trailingPE"),
        "市净率": info.get("priceToBook"),
        "简介": (info.get("longBusinessSummary") or "")[:500],
    }
    df = pd.DataFrame([keep])
    df.attrs[SOURCE_ATTR] = "yfinance"
    return df


def fetch_financial_indicators(symbol: str) -> pd.DataFrame:
    """年度利润表关键行 + 同比，转为「报告期一行」的窄表。"""
    stmt = yf.Ticker(symbol).income_stmt
    if stmt is None or stmt.empty:
        raise RuntimeError(f"yfinance 未返回 {symbol} 的利润表")
    stmt = stmt.T.sort_index()
    rows = []
    for period, row in stmt.iterrows():
        rows.append(
            {
                "日期": pd.to_datetime(period),
                "营业收入": row.get("Total Revenue"),
                "净利润": row.get("Net Income"),
            }
        )
    df = pd.DataFrame(rows).dropna(subset=["日期"]).sort_values("日期").reset_index(drop=True)
    df["主营业务收入增长率(%)"] = df["营业收入"].pct_change() * 100
    df["净利润增长率(%)"] = df["净利润"].pct_change() * 100
    df.attrs[SOURCE_ATTR] = "yfinance"
    return df


_NEWS_COLUMNS = ["发布时间", "新闻标题", "新闻内容", "文章来源", "新闻链接"]


def _parse_news_time(content: dict) -> pd.Timestamp:
    raw = content.get("pubDate") or content.get("providerPublishTime")
    if isinstance(raw, int | float):  # providerPublishTime 是 epoch 秒
        return pd.to_datetime(raw, unit="s", errors="coerce")
    return pd.to_datetime(raw, errors="coerce")


def fetch_news(symbol: str) -> pd.DataFrame:
    items = yf.Ticker(symbol).news or []
    rows = []
    for item in items:
        content = item.get("content", item)
        rows.append(
            {
                "发布时间": _parse_news_time(content),
                "新闻标题": content.get("title"),
                "新闻内容": (content.get("summary") or "")[:200],
                "文章来源": (content.get("provider") or {}).get("displayName")
                if isinstance(content.get("provider"), dict)
                else content.get("publisher"),
                "新闻链接": (content.get("canonicalUrl") or {}).get("url")
                if isinstance(content.get("canonicalUrl"), dict)
                else content.get("link"),
            }
        )
    # 空列表（无新闻 ticker / Yahoo 劣化响应）也返回标准列空帧并落缓存，
    # 而不是抛 KeyError 被误报为"获取失败"、每次都重新打 Yahoo
    df = pd.DataFrame(rows, columns=_NEWS_COLUMNS)
    if not df.empty:
        df = df.dropna(subset=["新闻标题"])
        df["发布时间"] = pd.to_datetime(df["发布时间"], errors="coerce").dt.tz_localize(None)
        df = df.sort_values("发布时间").reset_index(drop=True)
    df.attrs[SOURCE_ATTR] = "yfinance"
    return df
