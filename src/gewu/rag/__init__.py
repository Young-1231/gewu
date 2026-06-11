"""公告 RAG：巨潮定期报告全文问答。

设计取舍：检索用 BM25（jieba 分词）而非向量库——零额外 API 依赖、完全离线
可测、中文财报术语的词面匹配效果稳定；embedding 检索作为可插拔扩展留接口。
答案中的数字复用 fact_check 溯源审计：对照语料即检索到的公告片段。
"""

from gewu.rag.qa import AskResult, answer_over_chunks, ask

__all__ = ["AskResult", "answer_over_chunks", "ask"]
