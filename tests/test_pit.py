"""Point-in-Time 正确性——本项目评测可信度的根基。"""

from datetime import date

import pandas as pd

from gewu.data.pit import filter_periods_pit, report_visible_date


def test_statutory_visible_dates():
    assert report_visible_date(date(2025, 3, 31)) == date(2025, 4, 30)  # 一季报
    assert report_visible_date(date(2025, 6, 30)) == date(2025, 8, 31)  # 半年报
    assert report_visible_date(date(2025, 9, 30)) == date(2025, 10, 31)  # 三季报
    assert report_visible_date(date(2024, 12, 31)) == date(2025, 4, 30)  # 年报→次年

def test_filter_periods_pit_boundary():
    periods = pd.Series(["2024-09-30", "2024-12-31", "2025-03-31"])
    # 无真实公告日（法定截止日兜底）：2025-04-15 时三季报可见；年报与一季报（截止日均为 04-30）不可见
    mask = filter_periods_pit(periods, date(2025, 4, 15))
    assert mask.tolist() == [True, False, False]
    # 2025-04-30 截止日当天：全部可见
    mask = filter_periods_pit(periods, date(2025, 4, 30))
    assert mask.tolist() == [True, True, True]


def test_filter_periods_pit_real_announcement_dates():
    periods = pd.Series(["2024-09-30", "2024-12-31"])
    announced = {date(2024, 12, 31): date(2025, 4, 3)}  # 年报实际 04-03 公告
    # 04-10：真实公告日下年报已可见（法定规则要等 04-30）
    assert filter_periods_pit(periods, date(2025, 4, 10), announced).tolist() == [True, True]
    # 04-02：公告前一天仍不可见
    assert filter_periods_pit(periods, date(2025, 4, 2), announced).tolist() == [True, False]


def test_bundle_pit_no_leakage(data_service):
    """历史 as_of 下：行情/估值截断、财报按真实公告日（巨潮）判定可见——零未来信息。"""
    as_of = date(2025, 4, 15)
    bundle = data_service.load_bundle("600519", as_of)

    assert bundle.daily["date"].max().date() <= as_of
    assert bundle.valuation["date"].max().date() <= as_of
    # 夹具中 2024 年报真实公告日为 2025-04-03 → 04-15 已可见；2025Q1（04-25 公告）不可见
    latest_period = bundle.financial_indicators["日期"].max().date()
    assert latest_period == date(2024, 12, 31)
    period_columns = [c for c in bundle.financial_abstract.columns if str(c).isdigit()]
    assert max(period_columns) == "20241231"
    # 公告前一天：年报必须仍不可见
    before = data_service.load_bundle("600519", date(2025, 4, 2))
    assert before.financial_indicators["日期"].max().date() == date(2024, 9, 30)


def test_technical_indicators_follow_truncation(data_service):
    """技术指标必须在截断后的序列上计算（用截断日收盘价 == 摘要最新收盘价验证）。"""
    as_of = date(2025, 4, 15)
    bundle = data_service.load_bundle("600519", as_of)
    last_close = float(bundle.daily.iloc[-1]["close"])
    assert bundle.technical_summary["最新收盘价"] == round(last_close, 2)
