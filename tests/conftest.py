"""测试夹具：指向 tests/fixtures/cache 的只读数据缓存（2026-06-11 抓取的贵州茅台真实数据），
缓存有效期设为无穷大 → 测试完全离线、确定性。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from gewu.config import Settings
from gewu.data import DataService

FIXTURE_CACHE = Path(__file__).parent / "fixtures" / "cache"
FIXTURE_AS_OF = date(2026, 6, 11)  # 夹具抓取日：daily 最后一行为 2026-06-10


@pytest.fixture
def settings() -> Settings:
    return Settings(
        api_key=None,
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
        temperature=0.3,
        cache_dir=FIXTURE_CACHE,
        cache_max_age_days=10**9,
        request_interval=0.0,
        debate_rounds=1,
    )


@pytest.fixture
def data_service(settings) -> DataService:
    return DataService(settings)


@pytest.fixture
def bundle(data_service):
    return data_service.load_bundle("600519", FIXTURE_AS_OF)
