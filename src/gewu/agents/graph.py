"""LangGraph 拓扑装配。

START ─┬─ fundamental ─┐
       ├─ technical  ──┤
       ├─ news       ──┼─(屏障)→ bull ⇄ bear（N 轮）→ director → END
       └─ valuation  ──┘
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from gewu.agents.context import render_all, render_header
from gewu.agents.nodes import make_analyst_node, make_debater_node, make_director_node
from gewu.agents.state import ResearchState
from gewu.data.bundle import DataBundle
from gewu.llm import LLM

ANALYST_ROLES = ("fundamental", "technical", "news", "valuation")


def build_graph(llm: LLM, bundle: DataBundle, debate_rounds: int = 2):
    debate_rounds = max(1, debate_rounds)  # 拓扑保证 bull→bear 至少各发言一轮
    contexts = render_all(bundle)
    header = render_header(bundle)

    graph = StateGraph(ResearchState)
    for role in ANALYST_ROLES:
        graph.add_node(role, make_analyst_node(role, llm, contexts[role]))
        graph.add_edge(START, role)

    graph.add_node("bull", make_debater_node("bull", llm, header))
    graph.add_node("bear", make_debater_node("bear", llm, header))
    graph.add_node("director", make_director_node(llm, header, bundle.warnings))

    graph.add_edge(list(ANALYST_ROLES), "bull")  # 屏障：四分析师全部完成后开始辩论
    graph.add_edge("bull", "bear")

    def after_bear(state: ResearchState) -> str:
        bear_rounds = sum(1 for d in state.get("debate", []) if d["role"] == "bear")
        return "director" if bear_rounds >= debate_rounds else "bull"

    graph.add_conditional_edges("bear", after_bear, {"bull": "bull", "director": "director"})
    graph.add_edge("director", END)
    return graph.compile()
