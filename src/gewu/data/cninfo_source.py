"""巨潮资讯（cninfo）公告数据源：公告列表、定期报告真实公告日、PDF 正文抽取。

直接调用巨潮官方查询 API（akshare 的封装不暴露 PDF 附件路径）：
- 代码→orgId 映射：``/new/data/szse_stock.json``
- 公告查询：``/new/hisAnnouncement/query``（POST，分页）
- PDF 直链：``static.cninfo.com.cn/<adjunctUrl>``
"""

from __future__ import annotations

import logging
import re
from datetime import date
from io import BytesIO

import pandas as pd
import requests

from gewu.data.cache import SOURCE_ATTR

logger = logging.getLogger(__name__)

_BASE = "http://www.cninfo.com.cn"
_STATIC = "http://static.cninfo.com.cn/"
_HEADERS = {"User-Agent": "Mozilla/5.0 (gewu; +https://github.com/Young-1231/gewu)"}

# 定期报告类别（沪深）：年报/半年报/一季报/三季报
_PERIODIC_CATEGORIES = "category_ndbg_szsh;category_bndbg_szsh;category_yjdbg_szsh;category_sjdbg_szsh"

_TITLE_PERIOD = re.compile(r"(20\d{2})\s*年(年度报告|半年度报告|第一季度报告|第三季度报告)")
_PERIOD_END = {
    "年度报告": (12, 31),
    "半年度报告": (6, 30),
    "第一季度报告": (3, 31),
    "第三季度报告": (9, 30),
}

_org_id_cache: dict[str, str] = {}


def _org_id(symbol: str, session: requests.Session) -> str:
    if not _org_id_cache:
        data = session.get(f"{_BASE}/new/data/szse_stock.json", timeout=30).json()
        for item in data.get("stockList", []):
            _org_id_cache[item["code"]] = item["orgId"]
    if symbol not in _org_id_cache:
        raise RuntimeError(f"巨潮 orgId 未找到：{symbol}")
    return _org_id_cache[symbol]


def fetch_announcements(
    symbol: str,
    start: str = "2019-01-01",
    end: str | None = None,
    category: str | None = None,
    max_pages: int = 10,
) -> pd.DataFrame:
    """公告列表，标准列：公告标题/公告时间/adjunct_url/announcement_id。"""
    session = requests.Session()
    session.headers.update(_HEADERS)
    is_sh = symbol.startswith("6")
    end = end or str(date.today())
    rows: list[dict] = []
    for page in range(1, max_pages + 1):
        payload = {
            "pageNum": page,
            "pageSize": 30,
            "column": "sse" if is_sh else "szse",
            "tabName": "fulltext",
            "plate": "sh" if is_sh else "sz",
            "stock": f"{symbol},{_org_id(symbol, session)}",
            "seDate": f"{start}~{end}",
            "isHLtitle": "true",
        }
        if category:
            payload["category"] = category
        data = session.post(f"{_BASE}/new/hisAnnouncement/query", data=payload, timeout=30).json()
        for item in data.get("announcements") or []:
            rows.append(
                {
                    "公告标题": re.sub(r"</?em>", "", item.get("announcementTitle") or ""),
                    # announcementTime 是毫秒 epoch（UTC）；必须转回北京时间再去时区，
                    # 否则公告日早算一天 → 8 小时的前视泄漏窗口
                    "公告时间": pd.to_datetime(item.get("announcementTime"), unit="ms", utc=True)
                    .tz_convert("Asia/Shanghai")
                    .tz_localize(None),
                    "adjunct_url": item.get("adjunctUrl"),
                    "announcement_id": str(item.get("announcementId")),
                }
            )
        if not data.get("hasMore"):
            break
    df = pd.DataFrame(rows, columns=["公告标题", "公告时间", "adjunct_url", "announcement_id"])
    if not df.empty:
        df = df.sort_values("公告时间").reset_index(drop=True)
    df.attrs[SOURCE_ATTR] = "cninfo"
    return df


def parse_report_period(title: str) -> date | None:
    """从公告标题解析报告期末：``2025年年度报告`` → 2025-12-31。"""
    match = _TITLE_PERIOD.search(title)
    if not match:
        return None
    year, kind = int(match.group(1)), match.group(2)
    month, day = _PERIOD_END[kind]
    return date(year, month, day)


def fetch_report_dates(symbol: str, start: str = "2019-01-01") -> pd.DataFrame:
    """定期报告的**真实公告日**：每个报告期取最早公告时间（摘要与全文同日发布）。

    标准列：period_end / announced。供 PIT 模块替代法定披露截止日近似。
    """
    df = fetch_announcements(symbol, start=start, category=_PERIODIC_CATEGORIES)
    if df.empty:
        out = pd.DataFrame(columns=["period_end", "announced"])
        out.attrs[SOURCE_ATTR] = "cninfo"
        return out
    df = df.assign(period_end=df["公告标题"].map(parse_report_period))
    df = df.dropna(subset=["period_end"])
    out = (
        df.groupby("period_end", as_index=False)["公告时间"]
        .min()
        .rename(columns={"公告时间": "announced"})
        .sort_values("period_end")
        .reset_index(drop=True)
    )
    out["period_end"] = pd.to_datetime(out["period_end"])
    out.attrs[SOURCE_ATTR] = "cninfo"
    return out


def select_report_documents(announcements: pd.DataFrame, as_of: date) -> pd.DataFrame:
    """挑选适合问答的定期报告全文：剔除摘要/英文版/已取消，PIT 截断后每期保留最新一份。"""
    df = announcements[announcements["公告时间"] < pd.Timestamp(as_of) + pd.Timedelta(days=1)].copy()
    if df.empty:
        return df
    noise = df["公告标题"].str.contains("摘要|英文|已取消|提示性公告", na=False)
    df = df[~noise]
    df = df.assign(period_end=df["公告标题"].map(parse_report_period)).dropna(subset=["period_end"])
    df = df.sort_values("公告时间").groupby("period_end", as_index=False).last()
    return df.sort_values("period_end", ascending=False).reset_index(drop=True)


def download_pdf_text(adjunct_url: str) -> str:
    """下载公告 PDF 并抽取全文（页与页之间以分页标记分隔，供引用定位）。"""
    from pypdf import PdfReader

    response = requests.get(_STATIC + adjunct_url, headers=_HEADERS, timeout=120)
    response.raise_for_status()
    reader = PdfReader(BytesIO(response.content))
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(f"【第{number}页】\n{text}")
    return "\n\n".join(pages)
