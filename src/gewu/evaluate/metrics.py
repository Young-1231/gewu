"""绩效指标：累计/年化收益、夏普、最大回撤、方向命中率。"""

from __future__ import annotations

import pandas as pd


def max_drawdown(cumulative: pd.Series) -> float:
    """基于累计净值序列（首期前补 1.0）的最大回撤，返回负数百分比。"""
    curve = pd.concat([pd.Series([1.0]), cumulative], ignore_index=True)
    drawdown = curve / curve.cummax() - 1
    return float(drawdown.min() * 100)


def summarize_strategy(period_returns: pd.Series, periods_per_year: float) -> dict:
    """对期收益序列（小数）计算汇总指标。"""
    returns = period_returns.dropna()
    if returns.empty:
        return {}
    cumulative = (1 + returns).cumprod()
    total = float(cumulative.iloc[-1] - 1)
    years = len(returns) / periods_per_year
    # total <= -1（做空遇翻倍行情可达）时负底数的分数次幂会返回复数
    annualized = (1 + total) ** (1 / years) - 1 if years > 0 and total > -1 else float("nan")
    std = returns.std()
    sharpe = float(returns.mean() / std * periods_per_year**0.5) if std and std > 0 else float("nan")
    return {
        "期数": int(len(returns)),
        "平均期收益%": round(float(returns.mean() * 100), 2),
        "累计收益%": round(total * 100, 2),
        "年化收益%": round(annualized * 100, 2),
        "夏普": round(sharpe, 2),
        "最大回撤%": round(max_drawdown(cumulative), 2),
    }


def hit_rate(directions: pd.Series, forward_returns: pd.Series) -> float | None:
    """非中性观点的方向命中率：direction × 前向收益 > 0 记为命中。"""
    mask = (directions != 0) & forward_returns.notna()
    if not mask.any():
        return None
    return float(((directions[mask] * forward_returns[mask]) > 0).mean())
