"""SEC EDGAR 解析与 PE 序列构建（合成 companyfacts 结构，离线）。

注意：data.sec.gov 对部分地区 IP 返回 403，网络函数不在此测试；
解析逻辑基于 SEC 官方文档化的 XBRL companyfacts 结构。
"""

from datetime import date

import pandas as pd
import pytest

from gewu.data.edgar_source import build_pe_series, parse_annual_eps, parse_annual_financials


def _facts():
    def annual(year: int, value: float, filed: str) -> dict:
        return {
            "start": f"{year - 1}-10-01",
            "end": f"{year}-09-30",
            "val": value,
            "form": "10-K",
            "fp": "FY",
            "filed": filed,
        }

    quarterly = {  # 干扰项：季度条目（期长 ~90 天）必须被剔除
        "start": "2024-07-01", "end": "2024-09-30", "val": 1.0, "form": "10-Q", "fp": "Q3", "filed": "2024-11-01",
    }
    amendment = {  # 干扰项：同一期末的修正件（filed 更晚）应被排除，保留原始申报
        **annual(2024, 391_000_000_000.0, "2025-03-01"),
    }
    return {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            annual(2023, 383_000_000_000.0, "2023-11-03"),
                            annual(2024, 391_000_000_000.0, "2024-11-01"),
                            amendment,
                            quarterly,
                        ]
                    }
                },
                "NetIncomeLoss": {
                    "units": {
                        "USD": [
                            annual(2023, 97_000_000_000.0, "2023-11-03"),
                            annual(2024, 93_700_000_000.0, "2024-11-01"),
                        ]
                    }
                },
                "EarningsPerShareDiluted": {
                    "units": {
                        "USD/shares": [
                            annual(2023, 6.13, "2023-11-03"),
                            annual(2024, 6.08, "2024-11-01"),
                        ]
                    }
                },
            }
        }
    }


def test_parse_annual_financials():
    df = parse_annual_financials(_facts())
    assert len(df) == 2  # 季度与修正件被剔除
    latest = df.iloc[-1]
    assert pd.to_datetime(latest["日期"]).date() == date(2024, 9, 30)
    assert pd.to_datetime(latest["filed"]).date() == date(2024, 11, 1)  # 真实申报日（非修正件）
    assert latest["主营业务收入增长率(%)"] == pytest.approx(2.089, abs=0.01)


def test_parse_annual_eps():
    eps = parse_annual_eps(_facts())
    assert eps["eps"].tolist() == [6.13, 6.08]


def test_build_pe_series_is_point_in_time():
    eps = parse_annual_eps(_facts())
    daily = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-10-30", "2024-11-04", "2024-11-05"]),
            "close": [200.0, 200.0, 220.0],
        }
    )
    pe = build_pe_series(daily, eps)
    # 11-01 申报新 EPS 之前用旧 EPS(6.13)，之后用新 EPS(6.08)——阶梯切换即 PIT
    by_date = pe.set_index("date")["pe_static"]
    assert by_date[pd.Timestamp("2024-10-30")] == pytest.approx(200 / 6.13, rel=1e-4)
    assert by_date[pd.Timestamp("2024-11-04")] == pytest.approx(200 / 6.08, rel=1e-4)
    assert by_date[pd.Timestamp("2024-11-05")] == pytest.approx(220 / 6.08, rel=1e-4)


def test_build_pe_series_skips_non_positive_eps():
    eps = pd.DataFrame({"filed": pd.to_datetime(["2024-01-01"]), "eps": [-1.5]})
    daily = pd.DataFrame({"date": pd.to_datetime(["2024-02-01"]), "close": [100.0]})
    assert build_pe_series(daily, eps).empty  # 亏损公司不产生负 PE
