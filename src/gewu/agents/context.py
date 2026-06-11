"""把 DataBundle 渲染成各分析师的【数据上下文】文本。

这些文本同时是数字溯源审计的对照语料：研报中的每个实质性数字，
都必须能在这里出现过（见 fact_check.py）。
"""

from __future__ import annotations

import pandas as pd

from gewu.data.bundle import DataBundle

_FIN_COLUMNS = [
    "日期",
    "摊薄每股收益(元)",
    "主营业务收入增长率(%)",
    "净利润增长率(%)",
    "净资产收益率(%)",
    "销售毛利率(%)",
    "资产负债率(%)",
    "营业收入",
    "净利润",
]

_PROFILE_KEYS = ["公司名称", "A股简称", "所属行业", "行业", "板块", "主营业务", "经营范围", "入选指数"]


def _dict_lines(data: dict) -> str:
    return "\n".join(f"- {key}: {value}" for key, value in data.items()) or "（无数据）"


def render_header(bundle: DataBundle) -> str:
    profile_lines = "\n".join(
        f"- {key}: {str(bundle.profile[key])[:120]}" for key in _PROFILE_KEYS if key in bundle.profile
    )
    return (
        f"股票名称: {bundle.name}\n股票代码: {bundle.symbol}\n"
        f"分析基准日(as_of): {bundle.as_of}\n"
        f"市场: {'A股' if bundle.market == 'ashare' else '美股'}\n"
        f"公司概况:\n{profile_lines or '- （无概况数据）'}"
    )


def render_fundamental(bundle: DataBundle) -> str:
    parts = ["【最新财务摘要（Point-in-Time 已披露口径）】", _dict_lines(bundle.fundamental_summary)]
    fin = bundle.financial_indicators
    if fin is not None and not fin.empty:
        cols = [c for c in _FIN_COLUMNS if c in fin.columns]
        table = fin[cols].tail(8).copy()
        if "日期" in table.columns:
            table["日期"] = pd.to_datetime(table["日期"]).dt.date
        parts += ["", "【近8个报告期财务指标】", table.to_string(index=False)]
    else:
        parts += ["", "（财务指标明细不可用）"]
    return "\n".join(parts)


def render_technical(bundle: DataBundle) -> str:
    parts = ["【技术面预计算指标（基于前复权日线）】", _dict_lines(bundle.technical_summary)]
    daily = bundle.daily
    if not daily.empty:
        recent = daily.tail(10)[["date", "close"]].copy()
        recent["date"] = pd.to_datetime(recent["date"]).dt.date
        parts += ["", "【近10个交易日收盘价】", recent.to_string(index=False)]
    return "\n".join(parts)


def render_news(bundle: DataBundle, limit: int = 15) -> str:
    news = bundle.news
    if news is None or news.empty:
        return "【近期新闻】\n（窗口内无可用新闻——注意：免费新闻接口只保留近期条目，历史回测日期下属正常现象）"
    rows = []
    for _, item in news.tail(limit).iterrows():
        when = pd.to_datetime(item["发布时间"]).strftime("%Y-%m-%d")
        excerpt = str(item.get("新闻内容", ""))[:100].replace("\n", " ")
        rows.append(f"- [{when}] {item['新闻标题']}（{item.get('文章来源', '未知来源')}）\n  {excerpt}")
    return "【近期新闻（窗口45天，按时间升序）】\n" + "\n".join(rows)


def render_valuation(bundle: DataBundle) -> str:
    # 总市值带单位内联渲染，溯源审计才能识别"1.59万亿"这类换算表述
    summary = {
        key: (f"{value}亿元" if key == "总市值" else value)
        for key, value in bundle.valuation_summary.items()
    }
    parts = ["【估值预计算指标】", _dict_lines(summary)]
    valuation = bundle.valuation
    if valuation is not None and len(valuation) > 250:
        yearly = valuation.set_index("date").resample("YE").last().tail(5).reset_index()
        cols = [c for c in ("date", "pe_ttm", "pb") if c in yearly.columns]
        yearly = yearly[cols].copy()
        yearly["date"] = pd.to_datetime(yearly["date"]).dt.year
        parts += ["", "【近5年年末估值】", yearly.round(2).to_string(index=False)]
    return "\n".join(parts)


def render_peers(target: dict, peers: list[dict]) -> str:
    """同行对比表：目标公司置顶标注，数字与主上下文同口径进入审计语料。"""
    table = pd.DataFrame([{**target, "名称": f"{target['名称']}（本标的）"}, *peers])
    return "【同行对比表（与主标的同一 PIT 口径；总市值单位：亿元）】\n" + table.to_string(index=False)


def render_all(bundle: DataBundle) -> dict[str, str]:
    """每个分析师角色 → 其专属数据上下文。"""
    header = render_header(bundle)
    return {
        "fundamental": f"{header}\n\n{render_fundamental(bundle)}",
        "technical": f"{header}\n\n{render_technical(bundle)}",
        "news": f"{header}\n\n{render_news(bundle)}",
        "valuation": f"{header}\n\n{render_valuation(bundle)}",
    }
