"""数据层：多源自动降级的免费数据获取 + 本地缓存 + Point-in-Time 视图。

设计原则：
1. 多源降级——同一数据集按优先级尝试多个免费源（东财 → 新浪 → 腾讯），
   单一上游被限流/封禁不影响可用性（东财 push2 系接口在部分网络环境会拒绝连接，已实测）。
2. 缓存与限速——所有请求落本地 parquet 缓存并强制请求间隔，保护免费接口。
3. Point-in-Time——任何 as_of 日期下，只暴露彼时依法已披露的数据（见 pit.py），
   这是评测不泄漏未来信息的基础。
"""

from gewu.data.bundle import DataBundle
from gewu.data.service import DataService

__all__ = ["DataBundle", "DataService"]
