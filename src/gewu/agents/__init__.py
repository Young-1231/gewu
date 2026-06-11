"""Agent 层：LangGraph 编排的研究部门。

拓扑：四类分析师并行 → 多空研究员结构化辩论（可配轮数）→ 研究主管定评级
→（图外）研报装配 + 数字溯源审计。

与交易型 agent 框架（TradingAgents 等）的差别：本项目面向投研场景，
末端不是交易执行，而是「评级 + 可溯源研报」。
"""

from gewu.agents.pipeline import ResearchPipeline, ResearchResult

__all__ = ["ResearchPipeline", "ResearchResult"]
