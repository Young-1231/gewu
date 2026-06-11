"""端到端管线（MockLLM + 夹具数据，完全离线）。"""

from gewu.agents import ResearchPipeline
from gewu.agents.fact_check import AUDIT_END, AUDIT_START
from gewu.agents.nodes import RATINGS
from gewu.llm import MockLLM
from tests.conftest import FIXTURE_AS_OF


def test_full_pipeline_offline(settings, data_service):
    events: list[str] = []
    pipeline = ResearchPipeline(
        settings=settings, llm=MockLLM(), data_service=data_service, on_event=events.append
    )
    result = pipeline.run("600519", FIXTURE_AS_OF)

    # 图执行完整：四分析师 + 一轮辩论（settings.debate_rounds=1）+ 主管
    assert set(result.state["analyst_reports"]) == {"fundamental", "technical", "news", "valuation"}
    assert [d["role"] for d in result.state["debate"]] == ["bull", "bear"]
    assert result.decision["rating"] in RATINGS
    assert 0.0 <= result.decision["confidence"] <= 1.0

    # 研报结构完整且含审计标记
    for section in ("投资要点", "分析师观点", "多空辩论纪要", "数据与方法", "免责声明", "数字溯源审计"):
        assert section in result.report_md
    assert AUDIT_START in result.report_md and AUDIT_END in result.report_md

    # Mock 回显的都是上下文真实数字 → 溯源率应为 100%
    assert result.grounding.total > 0
    assert result.grounding.rate == 1.0

    # 事件流可观测
    assert any("研究主管" in event for event in events)


def test_debate_rounds_configurable(settings, data_service):
    settings2 = type(settings)(**{**settings.__dict__, "debate_rounds": 2})
    pipeline = ResearchPipeline(settings=settings2, llm=MockLLM(), data_service=data_service)
    result = pipeline.run("600519", FIXTURE_AS_OF)
    assert [d["role"] for d in result.state["debate"]] == ["bull", "bear", "bull", "bear"]
    assert [d["round"] for d in result.state["debate"]] == [1, 1, 2, 2]
