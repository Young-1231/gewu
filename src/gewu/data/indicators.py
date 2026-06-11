"""技术指标：纯 pandas 实现（MA / MACD / RSI / BOLL / 动量 / 波动率 / 量比）。

所有指标在 PIT 截断后的序列上计算，确保不引入未来数据。
"""

from __future__ import annotations

import pandas as pd


def enrich_indicators(daily: pd.DataFrame) -> pd.DataFrame:
    """在标准日线（date/open/high/low/close/volume）上追加指标列。"""
    df = daily.sort_values("date").reset_index(drop=True).copy()
    close = df["close"]

    df["ma5"] = close.rolling(5).mean()
    df["ma20"] = close.rolling(20).mean()
    df["ma60"] = close.rolling(60).mean()

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["macd_dif"] = ema12 - ema26
    df["macd_dea"] = df["macd_dif"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = 2 * (df["macd_dif"] - df["macd_dea"])

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    no_loss = loss == 0
    flat = no_loss & (gain == 0)
    rsi = 100 - 100 / (1 + gain / loss.where(~no_loss))
    # 窗口内无下跌 → 100；完全横盘（长期停牌等）→ 中性 50
    df["rsi14"] = rsi.where(~no_loss, 100.0).where(~flat, 50.0)

    mid = close.rolling(20).mean()
    std = close.rolling(20).std()
    df["boll_mid"] = mid
    df["boll_up"] = mid + 2 * std
    df["boll_dn"] = mid - 2 * std

    df["ret_20d"] = close.pct_change(20) * 100
    df["ret_60d"] = close.pct_change(60) * 100
    df["vol_20d"] = close.pct_change().rolling(20).std() * (252**0.5) * 100
    if "volume" in df.columns:
        base_volume = df["volume"].rolling(5).mean().shift(1)
        df["volume_ratio"] = df["volume"] / base_volume.where(base_volume > 0)  # 停牌零量不产生 inf

    return df


def summarize_technical(df: pd.DataFrame, window: int = 60) -> dict:
    """预计算供 LLM 引用的技术面数字——数字由代码算，LLM 只负责解读。"""
    if df.empty:
        return {}
    last = df.iloc[-1]
    recent = df.tail(window)
    summary: dict = {
        "最新交易日": str(pd.to_datetime(last["date"]).date()),
        "最新收盘价": round(float(last["close"]), 2),
        "区间涨跌幅": round(
            (float(last["close"]) / float(recent.iloc[0]["close"]) - 1) * 100, 2
        ),
        "区间最高": round(float(recent["high"].max()), 2),
        "区间最低": round(float(recent["low"].min()), 2),
    }

    def safe(name: str, digits: int = 2):
        value = last.get(name)
        if value is not None and pd.notna(value):
            summary[name] = round(float(value), digits)

    for col in ("ma20", "ma60", "rsi14", "macd_dif", "macd_dea", "ret_20d", "ret_60d", "vol_20d", "volume_ratio"):
        safe(col)

    if "ma20" in summary and "ma60" in summary:
        summary["均线形态"] = (
            "多头排列（价>MA20>MA60）"
            if summary["最新收盘价"] > summary["ma20"] > summary["ma60"]
            else "空头排列（价<MA20<MA60）"
            if summary["最新收盘价"] < summary["ma20"] < summary["ma60"]
            else "均线纠缠"
        )
    return summary
