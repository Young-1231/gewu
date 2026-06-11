"""SEC EDGAR 官方 XBRL API：美股财务（真实 filed 日期）与年度 EPS → PE 序列。

价值：filed 字段给出 10-K 的**真实申报日**，使美股 PIT 从"90 天保守滞后近似"
升级为真实可见日；年度稀释 EPS 按 filed 日期阶梯化后与日线相除，可得
PIT 正确的 PE(静态) 历史序列（进而算估值分位）。

可用性：data.sec.gov 对部分地区/数据中心 IP 返回 403（2026-06 于国内网络实测），
因此本模块在数据层中始终是**可选增强**：不可用时自动降级回 yfinance 并在
研报 warnings 中如实标注。SEC 公平访问政策要求 User-Agent 声明联系方式。
"""

from __future__ import annotations

import logging

import pandas as pd
import requests

from gewu.data.cache import SOURCE_ATTR

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "gewu/0.2 (https://github.com/Young-1231/gewu; huangfeiyang1231@gmail.com)"}
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

_REVENUE_CONCEPTS = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
)
_NET_INCOME_CONCEPTS = ("NetIncomeLoss",)
_EPS_CONCEPTS = ("EarningsPerShareDiluted", "EarningsPerShareBasic")

_cik_cache: dict[str, str] = {}


def _cik(symbol: str) -> str:
    if not _cik_cache:
        data = requests.get(_TICKERS_URL, headers=_HEADERS, timeout=30)
        data.raise_for_status()
        for item in data.json().values():
            _cik_cache[item["ticker"].upper()] = f"{item['cik_str']:010d}"
    cik = _cik_cache.get(symbol.upper())
    if not cik:
        raise RuntimeError(f"SEC ticker 映射中未找到 {symbol}")
    return cik


def fetch_company_facts(symbol: str) -> dict:
    response = requests.get(_FACTS_URL.format(cik=_cik(symbol)), headers=_HEADERS, timeout=60)
    response.raise_for_status()
    return response.json()


def _annual_entries(facts: dict, concepts: tuple[str, ...], unit: str) -> pd.DataFrame:
    """提取 10-K/FY 的年度条目（期长 300-400 天），同一期末取最早 filed（原始申报，排除修正件）。"""
    gaap = facts.get("facts", {}).get("us-gaap", {})
    for concept in concepts:
        entries = (gaap.get(concept) or {}).get("units", {}).get(unit) or []
        rows = []
        for entry in entries:
            if entry.get("form") != "10-K" or entry.get("fp") != "FY":
                continue
            start, end = entry.get("start"), entry.get("end")
            if not start or not end:
                continue
            days = (pd.Timestamp(end) - pd.Timestamp(start)).days
            if not 300 <= days <= 400:
                continue
            rows.append({"end": pd.Timestamp(end), "val": entry["val"], "filed": pd.Timestamp(entry["filed"])})
        if rows:
            df = pd.DataFrame(rows).sort_values(["end", "filed"])
            return df.groupby("end", as_index=False).first()
    return pd.DataFrame(columns=["end", "val", "filed"])


def parse_annual_financials(facts: dict) -> pd.DataFrame:
    """年度营收/净利 + 真实申报日，标准列：日期/营业收入/净利润/filed/同比增速。"""
    revenue = _annual_entries(facts, _REVENUE_CONCEPTS, "USD").rename(columns={"val": "营业收入"})
    income = _annual_entries(facts, _NET_INCOME_CONCEPTS, "USD").rename(columns={"val": "净利润"})
    if revenue.empty and income.empty:
        return pd.DataFrame()
    df = pd.merge(revenue, income, on="end", how="outer", suffixes=("", "_ni"))
    df["filed"] = df[[c for c in ("filed", "filed_ni") if c in df.columns]].max(axis=1)
    df = df.rename(columns={"end": "日期"}).sort_values("日期").reset_index(drop=True)
    if "营业收入" in df.columns:
        df["主营业务收入增长率(%)"] = df["营业收入"].pct_change() * 100
    if "净利润" in df.columns:
        df["净利润增长率(%)"] = df["净利润"].pct_change() * 100
    keep = [c for c in ("日期", "营业收入", "净利润", "filed", "主营业务收入增长率(%)", "净利润增长率(%)") if c in df.columns]
    return df[keep]


def parse_annual_eps(facts: dict) -> pd.DataFrame:
    """年度稀释 EPS + 申报日，标准列：end/eps/filed。"""
    eps = _annual_entries(facts, _EPS_CONCEPTS, "USD/shares").rename(columns={"val": "eps"})
    return eps


def fetch_financial_indicators(symbol: str) -> pd.DataFrame:
    df = parse_annual_financials(fetch_company_facts(symbol))
    if df.empty:
        raise RuntimeError(f"EDGAR 未返回 {symbol} 的年度财务数据")
    df.attrs[SOURCE_ATTR] = "sec_edgar"
    return df


def fetch_eps(symbol: str) -> pd.DataFrame:
    df = parse_annual_eps(fetch_company_facts(symbol))
    if df.empty:
        raise RuntimeError(f"EDGAR 未返回 {symbol} 的 EPS 数据")
    df.attrs[SOURCE_ATTR] = "sec_edgar"
    return df


def build_pe_series(daily: pd.DataFrame, eps: pd.DataFrame) -> pd.DataFrame:
    """PE(静态) 序列：每个交易日除以**彼时已申报**的最近年度 EPS（merge_asof on filed → 天然 PIT）。"""
    steps = eps.dropna(subset=["eps"]).sort_values("filed")[["filed", "eps"]]
    if steps.empty or daily.empty:
        return pd.DataFrame(columns=["date", "pe_static"])
    merged = pd.merge_asof(
        daily[["date", "close"]].sort_values("date"),
        steps,
        left_on="date",
        right_on="filed",
        direction="backward",
    )
    merged["pe_static"] = merged["close"] / merged["eps"].where(merged["eps"] > 0)
    out = merged[["date", "pe_static"]].dropna(subset=["pe_static"]).reset_index(drop=True)
    out.attrs[SOURCE_ATTR] = "sec_edgar+daily"
    return out
