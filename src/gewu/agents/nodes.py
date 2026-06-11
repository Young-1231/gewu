"""图节点工厂：分析师 / 多空研究员 / 研究主管。

节点是闭包（持有 llm 与渲染好的数据上下文），图状态里只流转文本与结论，
保持状态可序列化、可检查。
"""

from __future__ import annotations

import logging

from gewu.agents import prompts
from gewu.agents.state import ResearchState
from gewu.llm import LLM, extract_json

logger = logging.getLogger(__name__)

RATINGS = ("买入", "增持", "中性", "减持")
RATING_DIRECTION = {"买入": 1, "增持": 1, "中性": 0, "减持": -1}


def make_analyst_node(role: str, llm: LLM, context: str):
    system = prompts.ANALYST_SYSTEM[role]
    title = prompts.ANALYST_TITLES[role]

    def node(state: ResearchState) -> dict:
        user = f"【数据上下文】\n{context}\n\n请以{title}身份完成你的分析。"
        text = llm.complete(system, user)
        return {"analyst_reports": {role: text}}

    return node


def _analyst_digest(state: ResearchState) -> str:
    reports = state.get("analyst_reports", {})
    return "\n\n".join(
        f"### {prompts.ANALYST_TITLES[role]}\n{reports[role]}"
        for role in prompts.ANALYST_TITLES
        if role in reports
    )


def _debate_transcript(state: ResearchState) -> str:
    lines = [
        f"第{entry['round']}轮 {'多头' if entry['role'] == 'bull' else '空头'}：{entry['content']}"
        for entry in state.get("debate", [])
    ]
    return "\n\n".join(lines) or "（辩论尚未开始）"


def make_debater_node(side: str, llm: LLM, header: str):
    system = prompts.BULL_SYSTEM if side == "bull" else prompts.BEAR_SYSTEM

    def node(state: ResearchState) -> dict:
        round_no = sum(1 for d in state.get("debate", []) if d["role"] == side) + 1
        user = (
            f"【数据上下文】\n{header}\n\n【分析师报告】\n{_analyst_digest(state)}\n\n"
            f"【辩论记录】\n{_debate_transcript(state)}\n\n现在进行你的第{round_no}轮发言。"
        )
        text = llm.complete(system, user)
        return {"debate": [{"role": side, "round": round_no, "content": text}]}

    return node


def make_director_node(llm: LLM, header: str, warnings: list[str]):
    def node(state: ResearchState) -> dict:
        warning_text = "\n".join(f"- {w}" for w in warnings) or "- 无"
        user = (
            f"【数据上下文】\n{header}\n\n【分析师报告】\n{_analyst_digest(state)}\n\n"
            f"【多空辩论全文】\n{_debate_transcript(state)}\n\n"
            f"【数据质量警告】\n{warning_text}\n\n请给出最终裁决 JSON。"
        )
        raw = llm.complete(prompts.DIRECTOR_SYSTEM, user, json_mode=True)
        decision = _parse_decision(raw)
        return {"decision": decision}

    return node


def _parse_decision(raw: str) -> dict:
    try:
        data = extract_json(raw)
    except Exception:
        logger.warning("研究主管输出无法解析为 JSON，回退中性评级。原文：%.200s", raw)
        return {
            "rating": "中性",
            "confidence": 0.0,
            "summary": "主管输出解析失败，按流程回退为低置信度中性评级。",
            "key_points": [],
            "risks": ["模型输出格式异常"],
            "parse_error": True,
        }
    rating = str(data.get("rating", "中性"))
    if rating not in RATINGS:
        rating = "中性"
    try:
        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.5))))
    except (TypeError, ValueError):
        confidence = 0.5
    return {
        "rating": rating,
        "confidence": confidence,
        "summary": str(data.get("summary", "")),
        "key_points": [str(x) for x in data.get("key_points", []) if str(x).strip()],
        "risks": [str(x) for x in data.get("risks", []) if str(x).strip()],
    }
