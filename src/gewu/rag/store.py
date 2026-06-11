"""公告文档库：列表缓存、PDF 文本落盘缓存、分页分块。"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date

from gewu.config import Settings
from gewu.data import cninfo_source
from gewu.data.cache import DataCache

logger = logging.getLogger(__name__)

_PAGE_MARK = re.compile(r"【第(\d+)页】")

CHUNK_CHARS = 700
CHUNK_OVERLAP = 100


@dataclass
class Chunk:
    doc_title: str
    page: int
    text: str

    @property
    def citation(self) -> str:
        return f"《{self.doc_title}》第{self.page}页"


def split_pages(full_text: str) -> list[tuple[int, str]]:
    """按 download_pdf_text 的分页标记切回 (页码, 文本)。"""
    parts = _PAGE_MARK.split(full_text)
    pages = []
    for index in range(1, len(parts) - 1, 2):
        text = parts[index + 1].strip()
        if text:
            pages.append((int(parts[index]), text))
    return pages


def chunk_document(title: str, full_text: str) -> list[Chunk]:
    """页内滑窗分块：块长 ~700 字、重叠 100 字，块不跨页（保住页码引用精度）。"""
    chunks: list[Chunk] = []
    for page, text in split_pages(full_text):
        start = 0
        while start < len(text):
            piece = text[start : start + CHUNK_CHARS]
            if piece.strip():
                chunks.append(Chunk(doc_title=title, page=page, text=piece))
            if start + CHUNK_CHARS >= len(text):
                break
            start += CHUNK_CHARS - CHUNK_OVERLAP
    return chunks


class AnnouncementLibrary:
    """一只 A股的定期报告全文库（PIT：只暴露 as_of 前已公告的文档）。"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.cache = DataCache(settings.cache_dir, settings.cache_max_age_days)
        self.text_dir = settings.cache_dir / "pdf_text"

    def load_chunks(self, symbol: str, as_of: date | None = None, max_docs: int = 3) -> list[Chunk]:
        as_of = as_of or date.today()
        announcements = self.cache.get(
            f"ashare/{symbol}/announcements",
            lambda: cninfo_source.fetch_announcements(symbol),
            required_columns=("公告标题", "公告时间", "adjunct_url"),
        )
        documents = cninfo_source.select_report_documents(announcements, as_of).head(max_docs)
        if documents.empty:
            raise RuntimeError(f"{symbol} 在 {as_of} 前没有可用的定期报告全文")

        chunks: list[Chunk] = []
        for _, row in documents.iterrows():
            text = self._document_text(row["announcement_id"], row["adjunct_url"], row["公告标题"])
            if text:
                chunks.extend(chunk_document(row["公告标题"], text))
        if not chunks:
            raise RuntimeError(f"{symbol} 的公告 PDF 文本抽取均失败")
        return chunks

    def _document_text(self, announcement_id: str, adjunct_url: str, title: str) -> str:
        path = self.text_dir / f"{announcement_id}.txt"
        if path.exists():
            return path.read_text(encoding="utf-8")
        try:
            text = cninfo_source.download_pdf_text(adjunct_url)
        except Exception as error:
            logger.warning("公告《%s》PDF 抽取失败: %s", title, error)
            return ""
        self.text_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return text
