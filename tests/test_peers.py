"""行业对比分析师（peers）：快照、上下文渲染、图接入（离线）。"""

from gewu.agents import ResearchPipeline
from gewu.agents.context import render_peers
from gewu.llm import MockLLM
from tests.conftest import FIXTURE_AS_OF


def test_peer_snapshot_fields(data_service):
    snapshot = data_service.peer_snapshot("600519", FIXTURE_AS_OF)
    assert snapshot["名称"] == "贵州茅台"
    assert snapshot["PE(TTM)"] == 19.28
    assert snapshot["ROE%"] is not None


def test_render_peers_marks_target():
    target = {"代码": "600519", "名称": "贵州茅台", "PE(TTM)": 19.28}
    peer = {"代码": "000858", "名称": "五粮液", "PE(TTM)": 15.0}
    text = render_peers(target, [peer])
    assert "贵州茅台（本标的）" in text
    assert "五粮液" in text and "15.0" in text


def test_pipeline_with_peers_adds_fifth_analyst(settings, data_service):
    pipeline = ResearchPipeline(settings=settings, llm=MockLLM(), data_service=data_service)
    # 夹具只缓存了 600519，用自身作同行验证图拓扑与审计语料扩展
    result = pipeline.run("600519", FIXTURE_AS_OF, peers=["600519"])
    assert "peer" in result.state["analyst_reports"]
    assert "行业对比分析师" in result.report_md
    assert result.grounding.rate == 1.0  # 同行表数字进入审计语料

    # 不传 peers 时不应出现第五分析师
    plain = pipeline.run("600519", FIXTURE_AS_OF)
    assert "peer" not in plain.state["analyst_reports"]


def test_pipeline_tolerates_failed_peer(settings, data_service, monkeypatch):
    def failing_snapshot(symbol, as_of=None):
        raise RuntimeError("同行数据不可用")

    monkeypatch.setattr(data_service, "peer_snapshot", failing_snapshot)
    pipeline = ResearchPipeline(settings=settings, llm=MockLLM(), data_service=data_service)
    # 同行失败：不阻塞主流程，降级为四分析师并写入 warnings
    result = pipeline.run("600519", FIXTURE_AS_OF, peers=["999999"])
    assert "peer" not in result.state["analyst_reports"]
    assert any("999999" in w for w in result.bundle.warnings)
