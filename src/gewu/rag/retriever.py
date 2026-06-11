"""BM25 检索（jieba 搜索引擎分词）。"""

from __future__ import annotations

import logging
import warnings

with warnings.catch_warnings():
    # jieba 0.42 在 Python 3.12 下有上游 SyntaxWarning，不影响功能
    warnings.simplefilter("ignore", SyntaxWarning)
    import jieba

from rank_bm25 import BM25Okapi

from gewu.rag.store import Chunk

jieba.setLogLevel(logging.WARNING)


def _tokenize(text: str) -> list[str]:
    return [token for token in jieba.lcut_for_search(text) if token.strip()]


class BM25Retriever:
    def __init__(self, chunks: list[Chunk]):
        if not chunks:
            raise ValueError("文档库为空")
        self.chunks = chunks
        self._bm25 = BM25Okapi([_tokenize(chunk.text) for chunk in chunks])

    def search(self, query: str, top_k: int = 6) -> list[Chunk]:
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [self.chunks[i] for i in ranked[:top_k] if scores[i] > 0]
