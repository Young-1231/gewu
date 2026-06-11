"""代码评审确认问题的回归测试（2026-06-11 多 agent 评审，8 条确认）。"""

from datetime import date, timedelta

import pandas as pd

from gewu.config import Settings
from gewu.data.cache import DataCache
from gewu.data.indicators import enrich_indicators
from gewu.data.service import _profile_pit_minimize
from gewu.evaluate.backtest import _summarize
from gewu.evaluate.metrics import summarize_strategy


def test_cache_corruption_self_heals(tmp_path):
    """损坏的 parquet/meta 应被删除并按 cache miss 重抓，而不是在过期窗口内一直失败。"""
    cache = DataCache(tmp_path, max_age_days=1)
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return pd.DataFrame({"x": [1]})

    cache.get("k", fetch)
    data_path, meta_path = cache._paths("k")
    data_path.write_bytes(b"corrupted parquet")  # 模拟半截写入
    result = cache.get("k", fetch)
    assert calls["n"] == 2  # 自愈：重新抓取
    assert result["x"].tolist() == [1]

    meta_path.write_text("{truncated")  # 模拟损坏的 meta
    result = cache.get("k", fetch)
    assert calls["n"] == 3
    assert result["x"].tolist() == [1]


def test_cache_schema_validation_purges_wrong_columns(tmp_path):
    """读得出但 schema 不对的缓存（外部篡改/上游格式漂移）也要自愈，而不是 KeyError。"""
    cache = DataCache(tmp_path, max_age_days=1)
    cache.get("k", lambda: pd.DataFrame({"a": [1]}))  # 写入错误 schema
    healed = cache.get(
        "k", lambda: pd.DataFrame({"date": [1], "close": [2.0]}), required_columns=("date", "close")
    )
    assert list(healed.columns) == ["date", "close"]


def test_cache_write_is_atomic_no_tmp_left(tmp_path):
    cache = DataCache(tmp_path, max_age_days=1)
    cache.get("k", lambda: pd.DataFrame({"x": [1]}))
    leftovers = list(tmp_path.rglob("*.tmp"))
    assert leftovers == []


def test_profile_pit_minimize_strips_lookahead():
    profile = {
        "A股简称": "*ST某某",
        "公司名称": "某某股份有限公司",
        "所属行业": "白酒",
        "入选指数": "沪深300",
        "主营业务": "2025年起转型新能源",
    }
    warnings: list[str] = []
    yesterday = date.today() - timedelta(days=365)
    minimized, name = _profile_pit_minimize(profile, "*ST某某", "600000", yesterday, warnings)
    assert name == "某某"  # 剥离 *ST 前缀
    assert "入选指数" not in minimized
    assert "主营业务" not in minimized
    assert minimized["所属行业"] == "白酒"
    assert warnings  # 必须显式警告

    # 实时分析不动 profile
    warnings.clear()
    same, same_name = _profile_pit_minimize(profile, "*ST某某", "600000", date.today(), warnings)
    assert same == profile and same_name == "*ST某某" and not warnings


def test_config_expands_tilde(monkeypatch):
    monkeypatch.setenv("GEWU_CACHE_DIR", "~/.gewu/cache")
    settings = Settings.load()
    assert "~" not in str(settings.cache_dir)
    assert settings.cache_dir.is_absolute()


def test_annualized_guard_on_total_loss():
    """期收益 < -100%（做空遇翻倍行情）不得产生复数。"""
    stats = summarize_strategy(pd.Series([-1.2, 0.05]), periods_per_year=4)
    assert stats["年化收益%"] != stats["年化收益%"]  # NaN
    assert isinstance(stats["累计收益%"], float)


def test_summarize_handles_empty_and_none_momentum():
    assert "无评测点" in _summarize(pd.DataFrame(), horizon=60)
    # 动量方向全 0（新股池）→ momentum_hit 为 None，不得抛 TypeError
    points = pd.DataFrame(
        {
            "symbol": ["600519"],
            "as_of": [date(2025, 6, 30)],
            "rating": ["增持"],
            "confidence": [0.6],
            "direction": [1],
            "momentum_direction": [0],
            "forward_return": [0.05],
            "grounding_rate": [1.0],
            "error": [None],
        }
    )
    summary = _summarize(points, horizon=60)
    assert "N/A" in summary


def test_rsi_flat_series_is_neutral():
    daily = pd.DataFrame(
        {
            "date": pd.date_range("2025-01-01", periods=40, freq="B"),
            "open": [10.0] * 40,
            "high": [10.0] * 40,
            "low": [10.0] * 40,
            "close": [10.0] * 40,
            "volume": [0] * 40,
        }
    )
    enriched = enrich_indicators(daily)
    assert enriched["rsi14"].iloc[-1] == 50.0  # 横盘 → 中性而非 100
    assert not pd.Series(enriched["volume_ratio"]).isin([float("inf")]).any()  # 零量不产生 inf


def test_debate_rounds_clamped_to_one(settings, data_service):
    from gewu.agents import ResearchPipeline
    from gewu.llm import MockLLM
    from tests.conftest import FIXTURE_AS_OF

    bad = type(settings)(**{**settings.__dict__, "debate_rounds": 0})
    pipeline = ResearchPipeline(settings=bad, llm=MockLLM(), data_service=data_service)
    result = pipeline.run("600519", FIXTURE_AS_OF)
    assert [d["role"] for d in result.state["debate"]] == ["bull", "bear"]


def test_historical_bundle_carries_profile_warning(data_service):
    bundle = data_service.load_bundle("600519", date(2025, 4, 15))
    assert any("公司概况为当前快照" in w for w in bundle.warnings)
    assert "入选指数" not in bundle.profile
