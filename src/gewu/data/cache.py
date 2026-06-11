"""本地 parquet 缓存：键 → DataFrame，附带来源与抓取时间元数据。

健壮性约定：
- 原子写入（临时文件 + os.replace），进程被杀/磁盘满不会留下半截文件配新鲜元数据；
- 读到损坏的缓存（parquet/meta 解析失败）时删除该 key 并按 cache miss 重抓，可自愈；
- 不做跨进程文件锁：并发写同一 key 时 os.replace 保证读者看到的是完整的旧版或新版。
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

SOURCE_ATTR = "gewu_source"


class DataCache:
    """以 key（如 ``ashare/600519/daily``）寻址的 parquet 缓存。

    过期后重新抓取；抓取失败但存在旧缓存时退回旧缓存（宁可旧数据也不崩溃，
    并在 attrs 中标记 stale 供上层提示）。
    """

    def __init__(self, root: Path, max_age_days: float = 1.0):
        self.root = root
        self.max_age_days = max_age_days

    def _paths(self, key: str) -> tuple[Path, Path]:
        base = self.root / key
        return base.with_suffix(".parquet"), base.with_suffix(".meta.json")

    def get(
        self,
        key: str,
        fetch: Callable[[], pd.DataFrame],
        *,
        max_age_days: float | None = None,
        required_columns: tuple[str, ...] = (),
    ) -> pd.DataFrame:
        data_path, meta_path = self._paths(key)
        max_age = self.max_age_days if max_age_days is None else max_age_days

        def load_checked() -> pd.DataFrame:
            df = self._load(data_path, meta)
            missing = [c for c in required_columns if c not in df.columns]
            if missing:  # 读得出但 schema 不对（外部篡改/上游格式漂移落盘）同样视为损坏
                raise ValueError(f"缓存缺少必需列 {missing}")
            return df

        meta = self._read_meta(key) if data_path.exists() and meta_path.exists() else None
        if meta is not None:
            age_days = (time.time() - meta.get("fetched_at_ts", 0)) / 86400
            if age_days <= max_age:
                try:
                    return load_checked()
                except Exception as error:
                    logger.warning("缓存 %s 损坏(%s)，删除后重抓", key, error)
                    self._purge(key)
                    meta = None

        try:
            df = fetch()
        except Exception:
            if meta is not None:
                try:
                    stale = load_checked()
                except Exception:
                    self._purge(key)
                    raise  # 旧缓存也损坏：抛出原始抓取异常（from None 会掩盖它）
                logger.warning("抓取 %s 失败，退回旧缓存", key)
                stale.attrs["stale"] = True
                return stale
            raise

        self._atomic_write(df, data_path, meta_path)
        return df

    def _read_meta(self, key: str) -> dict | None:
        _, meta_path = self._paths(key)
        try:
            return json.loads(meta_path.read_text())
        except Exception as error:
            logger.warning("缓存元数据 %s 损坏(%s)，删除后重抓", key, error)
            self._purge(key)
            return None

    def _purge(self, key: str) -> None:
        for path in self._paths(key):
            path.unlink(missing_ok=True)

    @staticmethod
    def _atomic_write(df: pd.DataFrame, data_path: Path, meta_path: Path) -> None:
        data_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_data = data_path.with_name(data_path.name + ".tmp")
        df.to_parquet(tmp_data, index=False)
        os.replace(tmp_data, data_path)
        meta = {
            "fetched_at_ts": time.time(),
            "source": df.attrs.get(SOURCE_ATTR, "unknown"),
            "rows": int(len(df)),
        }
        tmp_meta = meta_path.with_name(meta_path.name + ".tmp")
        tmp_meta.write_text(json.dumps(meta, ensure_ascii=False))
        os.replace(tmp_meta, meta_path)

    @staticmethod
    def _load(data_path: Path, meta: dict) -> pd.DataFrame:
        df = pd.read_parquet(data_path)
        df.attrs[SOURCE_ATTR] = meta.get("source", "cache")
        return df
