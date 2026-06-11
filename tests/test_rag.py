"""公告 RAG：标题解析、文档挑选、分块、检索、问答（全离线）。"""

from datetime import date

import pandas as pd

from gewu.data.cninfo_source import parse_report_period, select_report_documents
from gewu.llm import MockLLM
from gewu.rag.qa import answer_over_chunks
from gewu.rag.retriever import BM25Retriever
from gewu.rag.store import chunk_document

SAMPLE_TEXT = (
    "【第1页】\n贵州茅台酒股份有限公司2025年年度报告\n\n"
    "【第2页】\n公司经本次董事会审议通过的利润分配预案为：以总股本为基数，"
    "向全体股东每股派发现金红利27.993元（含税）。报告期内营业收入为1,820.50亿元。\n\n"
    "【第3页】\n公司主营业务为茅台酒及系列酒的生产与销售。存货周转情况保持稳定。"
)


def _chunks():
    return chunk_document("2025年年度报告", SAMPLE_TEXT)


def test_parse_report_period():
    assert parse_report_period("贵州茅台2025年年度报告") == date(2025, 12, 31)
    assert parse_report_period("贵州茅台2025年半年度报告") == date(2025, 6, 30)
    assert parse_report_period("某公司2026年第一季度报告（修订版）") == date(2026, 3, 31)
    assert parse_report_period("关于召开股东大会的通知") is None


def test_select_report_documents_pit_and_dedup():
    df = pd.DataFrame(
        {
            "公告标题": [
                "贵州茅台2024年年度报告",
                "贵州茅台2024年年度报告摘要",
                "贵州茅台2025年第一季度报告",
                "贵州茅台2025年年度报告",
            ],
            "公告时间": pd.to_datetime(
                ["2025-04-03", "2025-04-03", "2025-04-30", "2026-04-17"]
            ),
            "adjunct_url": ["a.PDF", "b.PDF", "c.PDF", "d.PDF"],
            "announcement_id": ["1", "2", "3", "4"],
        }
    )
    picked = select_report_documents(df, as_of=date(2025, 6, 1))
    titles = picked["公告标题"].tolist()
    assert "贵州茅台2025年年度报告" not in titles  # PIT：未来公告不可见
    assert "贵州茅台2024年年度报告摘要" not in titles  # 摘要剔除
    assert titles[0] == "贵州茅台2025年第一季度报告"  # 最新报告期在前


def test_chunking_preserves_pages():
    chunks = _chunks()
    assert all(chunk.page in (1, 2, 3) for chunk in chunks)
    dividend_chunk = next(c for c in chunks if "27.993" in c.text)
    assert dividend_chunk.page == 2
    assert dividend_chunk.citation == "《2025年年度报告》第2页"


def test_bm25_retrieval_finds_relevant_page():
    retriever = BM25Retriever(_chunks())
    hits = retriever.search("每股分红 现金红利 多少", top_k=2)
    assert hits and hits[0].page == 2


def test_answer_over_chunks_with_audit():
    retriever = BM25Retriever(_chunks())
    hits = retriever.search("每股派发现金红利多少元", top_k=2)
    result = answer_over_chunks("600519", "分红方案？", hits, MockLLM())
    assert "27.993" in result.answer  # mock 回显片段中的真实数字
    assert result.grounding.rate == 1.0
    assert any("第2页" in source for source in result.sources)
