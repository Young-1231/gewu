"""DataService：缓存 + 多源抓取 + Point-in-Time 过滤 + 预计算摘要的统一入口。

关键纪律：**所有数字由代码计算，LLM 只做解读**。agent 看到的每个数字都先在
这里算好并进入 fact index，使研报数字可以逐一回溯（见 agents/fact_check.py）。
"""

from __future__ import annotations

import logging
import re
from datetime import date, timedelta

import pandas as pd

from gewu.config import Settings
from gewu.data import akshare_source, yahoo_source
from gewu.data.bundle import DataBundle
from gewu.data.cache import SOURCE_ATTR, DataCache
from gewu.data.indicators import enrich_indicators, summarize_technical
from gewu.data.pit import filter_periods_pit, report_visible_date

logger = logging.getLogger(__name__)

NEWS_WINDOW_DAYS = 45
US_REPORT_LAG_DAYS = 90  # 美股无公告日数据时的保守可见性滞后

# 公司概况是"抓取当日"的快照，无法回溯历史时点。历史模式（as_of < 今天）下只保留
# 慢变字段，并剥离简称中的风险警示前缀（*ST 等）——否则"未来才戴帽"的事实会
# 直接泄漏进回测上下文（评审发现，详见 docs/architecture.md §2.3）。
_HISTORY_SAFE_PROFILE_KEYS = ("公司名称", "A股简称", "股票简称", "所属行业", "行业", "板块")
_NAME_RISK_PREFIX = re.compile(r"^(\*?ST|S\*?ST|N|C|退市?)\s*", re.IGNORECASE)


def _profile_pit_minimize(
    profile: dict, name: str, symbol: str, as_of: date, warnings: list[str]
) -> tuple[dict, str]:
    """历史 as_of 下最小化 profile 的前视信息；实时分析不受影响。"""
    if as_of >= date.today():
        return profile, name
    clean_name = _NAME_RISK_PREFIX.sub("", name).strip() or symbol
    minimized = {}
    for key in _HISTORY_SAFE_PROFILE_KEYS:
        if key in profile:
            minimized[key] = _NAME_RISK_PREFIX.sub("", str(profile[key])).strip()
    warnings.append(
        "公司概况为当前快照而非历史时点：已剔除指数归属/业务描述并剥离 ST 等风险前缀，"
        "但行业等字段仍可能反映 as_of 之后的变化"
    )
    return minimized, clean_name


def detect_market(symbol: str) -> str:
    return "ashare" if re.fullmatch(r"\d{6}", symbol) else "us"


def _first_existing(row: pd.Series, candidates: list[str]) -> float | None:
    for name in candidates:
        if name in row.index and pd.notna(row[name]):
            value = pd.to_numeric(row[name], errors="coerce")
            if pd.notna(value):
                return float(value)
    return None


class DataService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.cache = DataCache(settings.cache_dir, settings.cache_max_age_days)

    def load_bundle(self, symbol: str, as_of: date | None = None) -> DataBundle:
        as_of = as_of or date.today()
        market = detect_market(symbol)
        loader = self._load_ashare if market == "ashare" else self._load_us
        return loader(symbol, as_of)

    _DAILY_REQUIRED = ("date", "close")

    def load_daily_full(self, symbol: str) -> pd.DataFrame:
        """未截断的全量日线——仅供评测模块计算前向收益，agent 不可见。"""
        if detect_market(symbol) == "ashare":
            return self.cache.get(
                f"ashare/{symbol}/daily",
                lambda: akshare_source.fetch_daily(symbol, self.settings.request_interval),
                required_columns=self._DAILY_REQUIRED,
            )
        return self.cache.get(
            f"us/{symbol}/daily",
            lambda: yahoo_source.fetch_daily(symbol),
            required_columns=self._DAILY_REQUIRED,
        )

    # ---------- A股 ----------

    def _load_ashare(self, symbol: str, as_of: date) -> DataBundle:
        interval = self.settings.request_interval
        sources: dict = {}
        warnings: list[str] = []

        def cached(dataset: str, fetch, **kwargs) -> pd.DataFrame | None:
            try:
                df = self.cache.get(f"ashare/{symbol}/{dataset}", fetch, **kwargs)
                sources[dataset] = df.attrs.get(SOURCE_ATTR, "unknown")
                if df.attrs.get("stale"):
                    warnings.append(f"{dataset} 使用了过期缓存（上游抓取失败）")
                return df
            except Exception as error:
                warnings.append(f"{dataset} 获取失败：{error}")
                logger.warning("数据集 %s/%s 获取失败: %s", symbol, dataset, error)
                return None

        daily_raw = cached(
            "daily",
            lambda: akshare_source.fetch_daily(symbol, interval),
            required_columns=self._DAILY_REQUIRED,
        )
        if daily_raw is None or daily_raw.empty:
            raise RuntimeError(f"{symbol} 行情数据不可用，无法继续分析")
        daily = daily_raw[daily_raw["date"].dt.date <= as_of].copy()
        if daily.empty:
            raise RuntimeError(f"{symbol} 在 {as_of} 之前无行情数据")
        daily = enrich_indicators(daily)

        fin = cached(
            "financial_indicators",
            lambda: akshare_source.fetch_financial_indicators(symbol, request_interval=interval),
        )
        if fin is not None and not fin.empty:
            fin = fin[filter_periods_pit(fin["日期"], as_of).to_numpy()].reset_index(drop=True)

        abstract = cached(
            "financial_abstract", lambda: akshare_source.fetch_financial_abstract(symbol, interval)
        )
        if abstract is not None and not abstract.empty:
            abstract = self._filter_abstract_pit(abstract, as_of)

        valuation = cached("valuation", lambda: akshare_source.fetch_valuation(symbol, interval))
        if valuation is not None and not valuation.empty:
            valuation = valuation[valuation["date"].dt.date <= as_of].reset_index(drop=True)

        news = cached("news", lambda: akshare_source.fetch_news(symbol, interval))
        if news is not None and not news.empty:
            lo = pd.Timestamp(as_of - timedelta(days=NEWS_WINDOW_DAYS))
            hi = pd.Timestamp(as_of) + pd.Timedelta(days=1)
            news = news[(news["发布时间"] >= lo) & (news["发布时间"] < hi)].reset_index(drop=True)
        if (news is None or news.empty) and as_of < date.today() - timedelta(days=7):
            warnings.append("历史回测日期下新闻覆盖有限（免费新闻接口只保留近期条目）")

        profile_df = cached("profile", lambda: akshare_source.fetch_profile(symbol, interval))
        profile = self._profile_to_dict(profile_df)
        name = str(profile.get("A股简称") or profile.get("股票简称") or profile.get("公司名称") or symbol)
        profile, name = _profile_pit_minimize(profile, name, symbol, as_of, warnings)

        return DataBundle(
            symbol=symbol,
            market="ashare",
            as_of=as_of,
            name=name,
            profile=profile,
            daily=daily,
            financial_indicators=fin,
            financial_abstract=abstract,
            valuation=valuation,
            news=news,
            technical_summary=summarize_technical(daily),
            fundamental_summary=self._fundamental_summary(fin),
            valuation_summary=self._valuation_summary(valuation),
            sources=sources,
            warnings=warnings,
        )

    @staticmethod
    def _filter_abstract_pit(abstract: pd.DataFrame, as_of: date) -> pd.DataFrame:
        keep = [c for c in abstract.columns if not re.fullmatch(r"\d{8}", str(c))]
        for col in abstract.columns:
            if re.fullmatch(r"\d{8}", str(col)):
                period_end = pd.to_datetime(str(col)).date()
                if report_visible_date(period_end) <= as_of:
                    keep.append(col)
        return abstract[keep]

    @staticmethod
    def _profile_to_dict(profile_df: pd.DataFrame | None) -> dict:
        if profile_df is None or profile_df.empty:
            return {}
        row = profile_df.iloc[0]
        return {str(k): str(v) for k, v in row.items() if pd.notna(v) and str(v).strip()}

    @staticmethod
    def _fundamental_summary(fin: pd.DataFrame | None) -> dict:
        if fin is None or fin.empty:
            return {}
        last = fin.iloc[-1]
        summary: dict = {"报告期": str(pd.to_datetime(last["日期"]).date())}
        mapping = {
            "营业收入同比": ["主营业务收入增长率(%)", "营业收入增长率(%)"],
            "归母净利润同比": ["净利润增长率(%)"],
            "ROE": ["净资产收益率(%)", "加权净资产收益率(%)"],
            "销售毛利率": ["销售毛利率(%)"],
            "资产负债率": ["资产负债率(%)"],
            "每股收益": ["摊薄每股收益(元)", "加权每股收益(元)"],
        }
        for label, candidates in mapping.items():
            value = _first_existing(last, candidates)
            if value is not None:
                summary[label] = round(value, 2)
        return summary

    @staticmethod
    def _valuation_summary(valuation: pd.DataFrame | None) -> dict:
        if valuation is None or valuation.empty:
            return {}
        window = valuation.tail(1250)  # 约5年交易日
        last = valuation.iloc[-1]
        summary: dict = {"估值日期": str(pd.to_datetime(last["date"]).date())}

        def add(col: str, label: str, percentile_label: str):
            if col in valuation.columns and pd.notna(last.get(col)):
                current = float(last[col])
                summary[label] = round(current, 2)
                series = pd.to_numeric(window[col], errors="coerce").dropna()
                if len(series) > 60:
                    summary[percentile_label] = round(float((series <= current).mean() * 100), 1)

        add("pe_ttm", "PE(TTM)", "PE五年分位")
        add("pb", "市净率", "PB五年分位")
        if "total_mv" in valuation.columns and pd.notna(last.get("total_mv")):
            summary["总市值"] = round(float(last["total_mv"]) / 1e8, 1)  # 亿元
        return summary

    # ---------- 美股（兼容层） ----------

    def _load_us(self, symbol: str, as_of: date) -> DataBundle:
        sources: dict = {}
        warnings: list[str] = ["美股为兼容档：估值历史分位与财务摘要深度弱于A股主战场"]

        def cached(dataset: str, fetch, **kwargs) -> pd.DataFrame | None:
            try:
                df = self.cache.get(f"us/{symbol}/{dataset}", fetch, **kwargs)
                sources[dataset] = df.attrs.get(SOURCE_ATTR, "unknown")
                return df
            except Exception as error:
                warnings.append(f"{dataset} 获取失败：{error}")
                return None

        daily_raw = cached(
            "daily",
            lambda: yahoo_source.fetch_daily(symbol),
            required_columns=self._DAILY_REQUIRED,
        )
        if daily_raw is None or daily_raw.empty:
            raise RuntimeError(f"{symbol} 行情数据不可用，无法继续分析")
        daily = daily_raw[daily_raw["date"].dt.date <= as_of].copy()
        if daily.empty:
            raise RuntimeError(f"{symbol} 在 {as_of} 之前无行情数据")
        daily = enrich_indicators(daily)

        fin = cached("financial_indicators", lambda: yahoo_source.fetch_financial_indicators(symbol))
        if fin is not None and not fin.empty:
            visible = fin["日期"].dt.date <= as_of - timedelta(days=US_REPORT_LAG_DAYS)
            fin = fin[visible.to_numpy()].reset_index(drop=True)

        news = cached("news", lambda: yahoo_source.fetch_news(symbol))
        if news is not None and not news.empty:
            hi = pd.Timestamp(as_of) + pd.Timedelta(days=1)
            news = news[news["发布时间"] < hi].reset_index(drop=True)

        profile_df = cached("profile", lambda: yahoo_source.fetch_profile(symbol))
        profile = self._profile_to_dict(profile_df)
        name = str(profile.get("公司名称") or symbol)
        profile, name = _profile_pit_minimize(profile, name, symbol, as_of, warnings)

        valuation_summary: dict = {}
        if as_of >= date.today() - timedelta(days=3):
            # yfinance 的 PE/PB 只有当前快照，无法回溯历史时点 → 仅实时分析提供
            for key, label in (("PE(TTM)", "PE(TTM)"), ("市净率", "市净率")):
                value = pd.to_numeric(profile.get(key), errors="coerce")
                if pd.notna(value):
                    valuation_summary[label] = round(float(value), 2)
        else:
            warnings.append("美股估值快照无法回溯到历史 as_of 时点，估值摘要为空")

        return DataBundle(
            symbol=symbol,
            market="us",
            as_of=as_of,
            name=name,
            profile=profile,
            daily=daily,
            financial_indicators=fin,
            financial_abstract=None,
            valuation=None,
            news=news,
            technical_summary=summarize_technical(daily),
            fundamental_summary=self._us_fundamental_summary(fin),
            valuation_summary=valuation_summary,
            sources=sources,
            warnings=warnings,
        )

    @staticmethod
    def _us_fundamental_summary(fin: pd.DataFrame | None) -> dict:
        if fin is None or fin.empty:
            return {}
        last = fin.iloc[-1]
        summary: dict = {"报告期": str(pd.to_datetime(last["日期"]).date())}
        for label, col in (("营业收入同比", "主营业务收入增长率(%)"), ("归母净利润同比", "净利润增长率(%)")):
            value = _first_existing(last, [col])
            if value is not None:
                summary[label] = round(value, 2)
        return summary
