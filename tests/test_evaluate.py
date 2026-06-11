"""评测模块：指标计算与离线回测管线。"""

from datetime import date

import pandas as pd
import pytest

from gewu.agents import ResearchPipeline
from gewu.evaluate.backtest import evaluation_dates, forward_return, run_backtest
from gewu.evaluate.metrics import hit_rate, max_drawdown, summarize_strategy
from gewu.llm import MockLLM


def test_max_drawdown_known_case():
    # 净值 1.0 → 1.2 → 0.9：最大回撤 = 0.9/1.2 - 1 = -25%
    cumulative = pd.Series([1.2, 0.9])
    assert max_drawdown(cumulative) == pytest.approx(-25.0)


def test_summarize_strategy_sane():
    returns = pd.Series([0.05, -0.02, 0.03, 0.01])
    stats = summarize_strategy(returns, periods_per_year=4)
    assert stats["期数"] == 4
    assert stats["累计收益%"] == pytest.approx(7.08, abs=0.05)
    assert stats["最大回撤%"] <= 0


def test_hit_rate_excludes_neutral():
    directions = pd.Series([1, -1, 0, 1])
    forwards = pd.Series([0.10, 0.05, 0.02, -0.03])
    # 非中性 3 笔：+1/+10%(中)、-1/+5%(错)、+1/-3%(错) → 1/3
    assert hit_rate(directions, forwards) == pytest.approx(1 / 3)


def test_forward_return_entry_after_as_of():
    daily = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07"]),
            "close": [10.0, 11.0, 12.0, 13.2, 14.0],
        }
    )
    # as_of=01-01：次日 11.0 开仓，持有 2 个交易日至 13.2 → +20%
    assert forward_return(daily, date(2025, 1, 1), horizon=2) == pytest.approx(0.2)
    # 前向数据不足 → None
    assert forward_return(daily, date(2025, 1, 6), horizon=10) is None


def test_evaluation_dates_quarterly():
    dates = evaluation_dates(date(2025, 1, 1), date(2025, 12, 31), "QE")
    assert dates == [date(2025, 3, 31), date(2025, 6, 30), date(2025, 9, 30), date(2025, 12, 31)]


def test_run_backtest_offline(settings, data_service):
    pipeline = ResearchPipeline(settings=settings, llm=MockLLM(), data_service=data_service)
    points, summary = run_backtest(
        pipeline, data_service, ["600519"], [date(2025, 6, 30), date(2025, 9, 30)], horizon=20
    )
    assert len(points) == 2
    assert points["error"].isna().all()
    assert points["forward_return"].notna().all()
    for keyword in ("回测汇总", "评级跟随", "买入持有基线", "评测局限"):
        assert keyword in summary
