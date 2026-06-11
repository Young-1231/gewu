"""Point-in-Time 走查回测：评级 → 前向收益 → 与基线同 panel 对照。

每个评测点 (symbol, as_of) 走与生产完全相同的 ResearchPipeline——
PIT 截断由数据层保证，评测不可能"偷看"未来。前向收益用全量日线
（agent 不可见）在事后计算。
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date

import pandas as pd

from gewu.agents.nodes import RATING_DIRECTION
from gewu.agents.pipeline import ResearchPipeline
from gewu.data.service import DataService
from gewu.evaluate.metrics import hit_rate, summarize_strategy

logger = logging.getLogger(__name__)

LIMITATIONS = """\
### 评测局限（依据 FINSABER, KDD 2026 的方法论自查）

- 股票池与时间窗有限，未覆盖完整牛熊周期；结论不可外推为"显著盈利能力"。
- 若股票池为当前指数成分，存在幸存者偏差（可用 `--universe csi300` 按历史成分缓解）。
- 评级为离散仓位（±1/0），未建模交易成本、滑点与流动性。
- LLM 投研已知系统性偏差：牛市过度保守、熊市过度激进——解读命中率时须分市场状态。
- 财报可见性按法定披露截止日保守判定：agent 可能比真实世界晚看到财报，评测结果偏保守而非偏乐观。
- 公司概况为当前快照：历史模式下已剔除指数归属/业务描述并剥离 ST 前缀，但行业等慢变字段仍有残余前视信息。
- 前复权价格以抓取日为锚：跨抓取日比较绝对价位不可靠，本评测只使用收益率（比值），不受影响。"""


def evaluation_dates(start: date, end: date, freq: str = "QE") -> list[date]:
    return [ts.date() for ts in pd.date_range(start, end, freq=freq)]


def forward_return(daily_full: pd.DataFrame, as_of: date, horizon: int) -> float | None:
    """as_of 之后第一个交易日开仓，持有 horizon 个交易日的收益（小数）。"""
    after = daily_full[daily_full["date"].dt.date > as_of].reset_index(drop=True)
    if len(after) < max(2, int(horizon * 0.7)):
        return None  # 前向数据不足
    entry = float(after.iloc[0]["close"])
    exit_index = min(horizon, len(after) - 1)
    return float(after.iloc[exit_index]["close"]) / entry - 1


def run_backtest(
    pipeline: ResearchPipeline,
    data_service: DataService,
    symbols: list[str],
    dates: list[date],
    horizon: int = 60,
    momentum_window: int = 60,
    on_event: Callable[[str], None] | None = None,
) -> tuple[pd.DataFrame, str]:
    """返回 (明细 DataFrame, markdown 汇总报告)。"""
    emit = on_event or (lambda message: logger.info(message))
    rows: list[dict] = []
    total = len(symbols) * len(dates)
    done = 0
    for as_of in dates:
        for symbol in symbols:
            done += 1
            emit(f"[{done}/{total}] {symbol} @ {as_of}")
            try:
                daily_full = data_service.load_daily_full(symbol)
                fwd = forward_return(daily_full, as_of, horizon)
                history = daily_full[daily_full["date"].dt.date <= as_of]
                momentum = None
                if len(history) > momentum_window:
                    momentum = (
                        float(history.iloc[-1]["close"]) / float(history.iloc[-1 - momentum_window]["close"]) - 1
                    )
                result = pipeline.run(symbol, as_of)
                rows.append(
                    {
                        "symbol": symbol,
                        "as_of": as_of,
                        "rating": result.decision.get("rating", "中性"),
                        "confidence": result.decision.get("confidence"),
                        "direction": RATING_DIRECTION.get(result.decision.get("rating", "中性"), 0),
                        "momentum_direction": 0 if momentum is None else (1 if momentum > 0 else -1),
                        "forward_return": fwd,
                        "grounding_rate": result.grounding.rate,
                        "error": None,
                    }
                )
            except Exception as error:
                logger.warning("评测点 %s@%s 失败: %s", symbol, as_of, error)
                rows.append(
                    {
                        "symbol": symbol,
                        "as_of": as_of,
                        "rating": None,
                        "confidence": None,
                        "direction": 0,
                        "momentum_direction": 0,
                        "forward_return": None,
                        "grounding_rate": None,
                        "error": str(error),
                    }
                )
    points = pd.DataFrame(rows)
    try:
        summary = _summarize(points, horizon)
    except Exception as error:  # 汇总失败绝不能拖累已经跑完（可能真实计费）的明细
        logger.exception("回测汇总生成失败")
        summary = f"## 回测汇总\n\n⚠️ 汇总生成失败：{error}\n\n明细数据完整，可从 points 重新计算。"
    return points, summary


def _summarize(points: pd.DataFrame, horizon: int) -> str:
    if points.empty:
        return "## 回测汇总\n\n（无评测点）"
    valid = points[points["error"].isna() & points["forward_return"].notna()].copy()
    periods_per_year = 252 / horizon

    def panel_returns(direction_column: str) -> pd.Series:
        per_date = valid.groupby("as_of").apply(
            lambda g: (g[direction_column] * g["forward_return"]).mean(),
            include_groups=False,
        )
        return per_date.sort_index()

    strategies = {
        "评级跟随（本系统）": panel_returns("direction"),
        "动量基线（60日）": panel_returns("momentum_direction"),
        "买入持有基线": valid.groupby("as_of")["forward_return"].mean().sort_index(),
    }

    lines = [
        "## 回测汇总",
        "",
        f"- 评测点：{len(points)}（有效 {len(valid)}，失败 {int(points['error'].notna().sum())}）",
        f"- 持有期：{horizon} 个交易日；同 panel 对照，等权组合",
    ]
    agent_hit = hit_rate(valid["direction"], valid["forward_return"])
    momentum_hit = hit_rate(valid["momentum_direction"], valid["forward_return"])
    if agent_hit is not None:
        momentum_text = f"{momentum_hit:.1%}" if momentum_hit is not None else "N/A"
        lines.append(f"- 非中性评级方向命中率：**{agent_hit:.1%}**（动量基线：{momentum_text}）")
    grounding = valid["grounding_rate"].dropna()
    if not grounding.empty:
        lines.append(f"- 平均数字溯源率：**{grounding.mean():.1%}**")
    lines += ["", "| 策略 | 期数 | 平均期收益% | 累计收益% | 年化收益% | 夏普 | 最大回撤% |", "|---|---|---|---|---|---|---|"]
    for name, returns in strategies.items():
        stats = summarize_strategy(returns, periods_per_year)
        if stats:
            lines.append(
                f"| {name} | {stats['期数']} | {stats['平均期收益%']} | {stats['累计收益%']} "
                f"| {stats['年化收益%']} | {stats['夏普']} | {stats['最大回撤%']} |"
            )
    rating_counts = points["rating"].value_counts(dropna=True).to_dict()
    lines += ["", f"- 评级分布：{rating_counts}", "", LIMITATIONS]
    return "\n".join(lines)
