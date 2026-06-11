"""LangGraph 状态定义。

DataFrame 不进图状态——agent 只通过预渲染的数据上下文（文本）接触数据，
这保证了「LLM 看到的」与「溯源审计核对的」是同一份语料。
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict


def merge_dicts(left: dict, right: dict) -> dict:
    return {**left, **right}


class ResearchState(TypedDict, total=False):
    symbol: str
    name: str
    as_of: str
    analyst_reports: Annotated[dict, merge_dicts]  # 角色 → 分析文本（四分析师并行写入）
    debate: Annotated[list, operator.add]  # [{role, round, content}]
    decision: dict  # {rating, confidence, summary, key_points, risks}
