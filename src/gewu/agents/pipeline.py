"""ResearchPipeline：数据 → 多 agent 图 → 研报 → 溯源审计 的端到端编排。"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from gewu.agents import fact_check
from gewu.agents.context import render_all
from gewu.agents.graph import build_graph
from gewu.agents.state import ResearchState
from gewu.config import Settings
from gewu.data import DataBundle, DataService
from gewu.llm import LLM, build_llm
from gewu.report.builder import build_report

logger = logging.getLogger(__name__)

_NODE_LABELS = {
    "fundamental": "基本面分析师",
    "technical": "技术面分析师",
    "news": "新闻舆情分析师",
    "valuation": "估值分析师",
    "peer": "行业对比分析师",
    "bull": "多头研究员",
    "bear": "空头研究员",
    "director": "研究主管",
}


@dataclass
class ResearchResult:
    symbol: str
    name: str
    as_of: date
    state: ResearchState
    decision: dict
    grounding: fact_check.GroundingResult
    report_md: str
    bundle: DataBundle


class ResearchPipeline:
    def __init__(
        self,
        settings: Settings | None = None,
        llm: LLM | None = None,
        data_service: DataService | None = None,
        on_event: Callable[[str], None] | None = None,
    ):
        self.settings = settings or Settings.load()
        self.llm = llm if llm is not None else build_llm(self.settings)
        self.data = data_service or DataService(self.settings)
        self._emit = on_event or (lambda message: logger.info(message))

    def run(
        self,
        symbol: str,
        as_of: date | None = None,
        charts_dir: Path | None = None,
        peers: list[str] | None = None,
    ) -> ResearchResult:
        self._emit(f"加载数据：{symbol} @ {as_of or '今天'}")
        bundle = self.data.load_bundle(symbol, as_of)
        self._emit(
            f"数据就绪：{bundle.name}，来源 {bundle.sources}"
            + (f"，警告 {len(bundle.warnings)} 条" if bundle.warnings else "")
        )

        peer_context = None
        if peers:
            snapshots = []
            for peer in peers:
                try:
                    snapshots.append(self.data.peer_snapshot(peer, bundle.as_of))
                    self._emit(f"同行数据就绪：{peer}")
                except Exception as error:
                    bundle.warnings.append(f"同行 {peer} 数据获取失败：{error}")
            if snapshots:
                from gewu.agents.context import render_peers

                peer_context = render_peers(self.data.peer_snapshot(symbol, bundle.as_of), snapshots)

        graph = build_graph(self.llm, bundle, self.settings.debate_rounds, peer_context)
        initial: ResearchState = {
            "symbol": bundle.symbol,
            "name": bundle.name,
            "as_of": str(bundle.as_of),
        }
        state: ResearchState = {}
        for mode, chunk in graph.stream(initial, stream_mode=["updates", "values"]):
            if mode == "updates":
                for node_name in chunk:
                    self._emit(f"完成：{_NODE_LABELS.get(node_name, node_name)}")
            else:
                state = chunk

        decision = state.get("decision", {})
        charts: list[tuple[str, str]] | None = None
        if charts_dir is not None:
            from gewu.report.charts import render_charts

            charts = render_charts(bundle, charts_dir)
            if charts:
                self._emit(f"图表生成：{len(charts)} 张")
        report_body = build_report(bundle, state, charts)

        corpus = "\n\n".join(render_all(bundle).values())
        if peer_context:
            corpus += "\n\n" + peer_context  # 同行表数字同样要可溯源
        grounding = fact_check.audit(fact_check.extract_audit_region(report_body), corpus)
        report_md = report_body + "\n" + grounding.to_markdown()
        rate_text = f"{grounding.rate:.1%}" if grounding.rate is not None else "N/A"
        self._emit(f"溯源审计：{grounding.grounded}/{grounding.total} 可溯源（{rate_text}）")

        return ResearchResult(
            symbol=bundle.symbol,
            name=bundle.name,
            as_of=bundle.as_of,
            state=state,
            decision=decision,
            grounding=grounding,
            report_md=report_md,
            bundle=bundle,
        )
