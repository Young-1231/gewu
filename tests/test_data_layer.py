"""数据层：缓存语义、指标计算、市场识别。"""

from datetime import date

import pandas as pd
import pytest

from gewu.data.cache import DataCache
from gewu.data.indicators import enrich_indicators, summarize_technical
from gewu.data.service import detect_market


def test_detect_market():
    assert detect_market("600519") == "ashare"
    assert detect_market("000858") == "ashare"
    assert detect_market("AAPL") == "us"
    assert detect_market("BRK-B") == "us"


def test_cache_roundtrip_and_no_refetch(tmp_path):
    cache = DataCache(tmp_path, max_age_days=1)
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        df = pd.DataFrame({"x": [1, 2]})
        df.attrs["gewu_source"] = "unit-test"
        return df

    first = cache.get("a/b/c", fetch)
    second = cache.get("a/b/c", fetch)
    assert calls["n"] == 1  # 第二次命中缓存
    assert second.attrs["gewu_source"] == "unit-test"
    pd.testing.assert_frame_equal(first, second)


def test_cache_falls_back_to_stale_on_fetch_error(tmp_path):
    cache = DataCache(tmp_path, max_age_days=0)  # 立即过期，强制重新抓取

    def good():
        return pd.DataFrame({"x": [1]})

    def bad():
        raise RuntimeError("上游挂了")

    cache.get("k", good)
    stale = cache.get("k", bad)  # 抓取失败 → 退回旧缓存
    assert stale.attrs.get("stale") is True
    with pytest.raises(RuntimeError):
        cache.get("never-cached", bad)


def test_indicators_and_summary():
    closes = [100 + i * 0.5 for i in range(80)]
    daily = pd.DataFrame(
        {
            "date": pd.date_range("2025-01-01", periods=80, freq="B"),
            "open": closes,
            "high": [c * 1.01 for c in closes],
            "low": [c * 0.99 for c in closes],
            "close": closes,
            "volume": [1_000_000] * 80,
        }
    )
    enriched = enrich_indicators(daily)
    last = enriched.iloc[-1]
    assert last["ma20"] == pytest.approx(sum(closes[-20:]) / 20)
    assert 50 < last["rsi14"] <= 100  # 单边上涨 → RSI 偏强

    summary = summarize_technical(enriched)
    assert summary["最新收盘价"] == round(closes[-1], 2)
    assert summary["均线形态"].startswith("多头排列")


def test_bundle_summaries_match_fixture(bundle):
    """夹具数据（2026-06-11 抓取的贵州茅台）关键数字回归。"""
    assert bundle.name == "贵州茅台"
    assert bundle.technical_summary["最新收盘价"] == 1275.88
    assert bundle.fundamental_summary["报告期"] == "2026-03-31"
    assert bundle.valuation_summary["PE(TTM)"] == 19.28
    assert date(2025, 1, 1) < bundle.as_of
