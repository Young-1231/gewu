"""公告问答：检索 → 引用式回答 → 数字溯源审计。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from gewu.agents import fact_check
from gewu.config import Settings
from gewu.data.service import detect_market
from gewu.llm import LLM
from gewu.rag.retriever import BM25Retriever
from gewu.rag.store import AnnouncementLibrary, Chunk

QA_SYSTEM = """你是上市公司公告问答助手。
规则（最高优先级）：
1. 只依据【公告片段】回答；片段中没有的信息明确说"公告片段中未找到"，禁止凭通识补充。
2. 引用的每个关键数字与事实后面用括号标注来源，如（《2025年年度报告》第12页）。
3. 数字保持原值与单位，不要换算。
4. 简体中文作答，先给直接答案，再列依据。"""


@dataclass
class AskResult:
    symbol: str
    question: str
    answer: str
    sources: list[str]
    grounding: fact_check.GroundingResult
    chunks: list[Chunk]


def answer_over_chunks(symbol: str, question: str, chunks: list[Chunk], llm: LLM) -> AskResult:
    """对已检索的片段做问答（与文档获取解耦，便于离线测试）。"""
    context = "\n\n".join(f"[{i + 1}] {c.citation}\n{c.text}" for i, c in enumerate(chunks))
    user = f"【公告片段】\n{context}\n\n【问题】{question}"
    answer = llm.complete(QA_SYSTEM, user)
    grounding = fact_check.audit(answer, context)
    sources = sorted({chunk.citation for chunk in chunks})
    return AskResult(
        symbol=symbol,
        question=question,
        answer=answer,
        sources=sources,
        grounding=grounding,
        chunks=chunks,
    )


def ask(
    symbol: str,
    question: str,
    llm: LLM,
    settings: Settings,
    as_of: date | None = None,
    top_k: int = 6,
    max_docs: int = 3,
) -> AskResult:
    if detect_market(symbol) != "ashare":
        raise ValueError("公告问答目前仅支持 A股（巨潮资讯）；美股财报问答在路线图（SEC EDGAR 全文）")
    library = AnnouncementLibrary(settings)
    chunks = library.load_chunks(symbol, as_of, max_docs=max_docs)
    retriever = BM25Retriever(chunks)
    hits = retriever.search(question, top_k=top_k)
    if not hits:
        raise RuntimeError("检索不到与问题相关的公告片段，请换种问法或增加 --docs")
    return answer_over_chunks(symbol, question, hits, llm)
