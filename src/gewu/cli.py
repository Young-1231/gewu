"""格物 Gewu 命令行入口。

示例：
    gewu analyze 600519                     # 实时分析（需 API key）
    gewu analyze 600519 --mock              # 离线演示（无需 key）
    gewu analyze 600519 --as-of 2025-04-15  # 历史时点（PIT 视图）
    gewu backtest --symbols 600519,000858 --start 2024-06-30 --end 2025-06-30 --mock
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

import gewu
from gewu.config import Settings

app = typer.Typer(no_args_is_help=True, help="格物 Gewu — A股优先的金融研究多智能体框架")
console = Console()


def _parse_date(text: str | None) -> date | None:
    return date.fromisoformat(text) if text else None


def _emit(message: str) -> None:
    console.print(f"[dim]· {message}[/dim]")


@app.command()
def analyze(
    symbol: str = typer.Argument(..., help="股票代码：A股 6 位数字（600519）或美股 ticker（AAPL）"),
    as_of: str = typer.Option(None, "--as-of", help="分析基准日 YYYY-MM-DD（默认今天）；历史日期触发 PIT 视图"),
    mock: bool = typer.Option(False, "--mock", help="Mock 模式：不调用真实 LLM（数据抓取仍需联网，缓存后可离线）"),
    out: Path = typer.Option(Path("reports"), "--out", help="研报输出目录"),
    rounds: int = typer.Option(None, "--rounds", help="多空辩论轮数（默认 2）"),
    no_charts: bool = typer.Option(False, "--no-charts", help="跳过图表生成"),
    peers: str = typer.Option(None, "--peers", help="逗号分隔的同行代码，启用行业对比分析师（如 000858,000568）"),
):
    """生成一份带数字溯源审计的研究报告。"""
    from gewu.agents import ResearchPipeline
    from gewu.llm import build_llm

    settings = Settings.load(debate_rounds=rounds)
    pipeline = ResearchPipeline(
        settings=settings, llm=build_llm(settings, mock=mock), on_event=_emit
    )
    target_date = _parse_date(as_of)
    out.mkdir(parents=True, exist_ok=True)
    peer_list = [p.strip() for p in peers.split(",") if p.strip()] if peers else None

    result = pipeline.run(
        symbol, target_date, charts_dir=None if no_charts else out, peers=peer_list
    )

    report_path = out / f"{result.symbol}_{result.as_of}.md"
    report_path.write_text(result.report_md, encoding="utf-8")

    rate = result.grounding.rate
    console.print(
        Panel.fit(
            f"[bold]{result.name}（{result.symbol}）[/bold] @ {result.as_of}\n"
            f"评级：[bold]{result.decision.get('rating', 'N/A')}[/bold]"
            f"（置信度 {result.decision.get('confidence', 0):.0%}）\n"
            f"数字溯源率：{f'{rate:.1%}' if rate is not None else 'N/A'}"
            f"（{result.grounding.grounded}/{result.grounding.total}）\n"
            f"报告：{report_path}",
            title="格物 Gewu",
            border_style="cyan",
        )
    )
    if mock:
        console.print("[yellow]⚠ Mock 模式输出仅用于演示流程，不代表真实模型分析。[/yellow]")


@app.command()
def backtest(
    symbols: str = typer.Option(None, "--symbols", help="逗号分隔的股票代码；与 --universe 二选一"),
    universe: str = typer.Option(None, "--universe", help="csi300：按 start 日期的沪深300历史成分（防幸存者偏差）"),
    sample: int = typer.Option(10, "--sample", help="从 universe 中可复现实验抽样的数量"),
    start: str = typer.Option(..., "--start", help="评测起始日 YYYY-MM-DD"),
    end: str = typer.Option(None, "--end", help="评测结束日（默认今天）"),
    freq: str = typer.Option("QE", "--freq", help="评测频率（pandas 频率串，默认季度末 QE）"),
    horizon: int = typer.Option(60, "--horizon", help="前向持有期（交易日）"),
    mock: bool = typer.Option(False, "--mock", help="Mock 模式：不调用真实 LLM，验证评测管线本身"),
    seed: int = typer.Option(42, "--seed", help="抽样随机种子（可复现）"),
    out: Path = typer.Option(Path("reports/backtest"), "--out", help="结果输出目录"),
):
    """Point-in-Time 走查回测：评级 vs 动量/买入持有基线。"""
    from gewu.agents import ResearchPipeline
    from gewu.data import DataService
    from gewu.evaluate import run_backtest
    from gewu.evaluate.backtest import evaluation_dates
    from gewu.evaluate.universe import csi300_members, sample_universe
    from gewu.llm import build_llm

    start_date = _parse_date(start)
    end_date = _parse_date(end) or date.today()
    if symbols:
        pool = [s.strip() for s in symbols.split(",") if s.strip()]
    elif universe == "csi300":
        console.print(f"[dim]按 {start_date} 的沪深300历史成分构建股票池…[/dim]")
        pool = sample_universe(csi300_members(start_date), sample, seed)
    else:
        raise typer.BadParameter("必须提供 --symbols 或 --universe csi300")

    dates = evaluation_dates(start_date, end_date, freq)
    if not dates:
        raise typer.BadParameter("评测窗口内没有评测日，请检查 --start/--end/--freq")
    console.print(f"股票池 {len(pool)} 只 × 评测日 {len(dates)} 个 = {len(pool) * len(dates)} 个评测点")

    # 评测可能耗时数小时且真实计费——开跑前先确认输出目录可写
    out.mkdir(parents=True, exist_ok=True)
    probe = out / ".write_probe"
    probe.write_text("")
    probe.unlink()

    settings = Settings.load()
    data_service = DataService(settings)
    pipeline = ResearchPipeline(
        settings=settings, llm=build_llm(settings, mock=mock), data_service=data_service
    )
    points, summary = run_backtest(
        pipeline, data_service, pool, dates, horizon=horizon, on_event=_emit
    )

    points_path = out / "points.csv"
    summary_path = out / "summary.md"
    points.to_csv(points_path, index=False)  # 明细先落盘，汇总在后
    header = (
        f"# 回测报告\n\n- 模式：{'Mock（管线验证）' if mock else '真实 LLM'}\n"
        f"- 窗口：{start_date} → {end_date}（{freq}）\n- 股票池：{len(pool)} 只\n\n"
    )
    summary_path.write_text(header + summary, encoding="utf-8")
    console.print(summary)
    console.print(f"\n明细：{points_path}\n汇总：{summary_path}")


@app.command()
def ask(
    symbol: str = typer.Argument(..., help="A股代码（6 位数字）"),
    question: str = typer.Argument(..., help="针对公司定期报告的问题"),
    as_of: str = typer.Option(None, "--as-of", help="PIT 基准日：只用此前已公告的报告回答"),
    mock: bool = typer.Option(False, "--mock", help="Mock 模式：不调用真实 LLM"),
    top_k: int = typer.Option(6, "--top-k", help="检索片段数"),
    docs: int = typer.Option(3, "--docs", help="纳入问答的最近定期报告份数"),
):
    """公告 RAG 问答：基于巨潮定期报告全文，带页码引用与数字溯源审计。"""
    from gewu.llm import build_llm
    from gewu.rag import ask as rag_ask

    settings = Settings.load()
    console.print("[dim]· 加载公告库（首次需下载 PDF，约数十秒）…[/dim]")
    result = rag_ask(
        symbol, question, build_llm(settings, mock=mock), settings,
        as_of=_parse_date(as_of), top_k=top_k, max_docs=docs,
    )
    console.print(Panel(result.answer, title=f"{symbol} · 公告问答", border_style="cyan"))
    rate = result.grounding.rate
    console.print(
        f"依据文档：{'；'.join(result.sources)}\n"
        f"数字溯源率：{f'{rate:.1%}' if rate is not None else 'N/A'}"
        f"（{result.grounding.grounded}/{result.grounding.total}）"
    )
    for item in result.grounding.ungrounded[:5]:
        console.print(f"[yellow]⚠ 待核验数字：{item['text']} —— …{item['context']}…[/yellow]")
    if mock:
        console.print("[yellow]⚠ Mock 模式输出仅用于演示流程。[/yellow]")


@app.command()
def fetch(
    symbol: str = typer.Argument(..., help="股票代码"),
    as_of: str = typer.Option(None, "--as-of", help="基准日 YYYY-MM-DD"),
):
    """预热数据缓存（不调用 LLM）。"""
    from gewu.data import DataService

    service = DataService(Settings.load())
    bundle = service.load_bundle(symbol, _parse_date(as_of))
    console.print(f"已缓存 {bundle.name}（{bundle.symbol}）@ {bundle.as_of}")
    console.print(f"数据源：{bundle.sources}")
    for warning in bundle.warnings:
        console.print(f"[yellow]⚠ {warning}[/yellow]")


@app.command()
def benchmark(
    data: Path = typer.Option(Path("data/benchmark_sample.jsonl"), "--data", help="题集（.jsonl/.csv，FinEval 兼容字段）"),
    limit: int = typer.Option(None, "--limit", help="只跑前 N 题"),
    mock: bool = typer.Option(False, "--mock", help="Mock 模式：验证跑分管线本身"),
    out: Path = typer.Option(Path("reports/benchmark"), "--out", help="结果输出目录"),
):
    """金融多选题基准跑分（FinEval 兼容；仓库不分发基准数据，自带格式样例）。"""
    from gewu.evaluate.benchmark import load_questions, run_benchmark
    from gewu.llm import build_llm

    settings = Settings.load()
    questions = load_questions(data)
    console.print(f"题集：{data}（{len(questions)} 题）")
    out.mkdir(parents=True, exist_ok=True)

    details, result = run_benchmark(build_llm(settings, mock=mock), questions, limit=limit, on_event=_emit)
    details.to_csv(out / "details.csv", index=False)
    summary = result.to_markdown(str(data))
    (out / "summary.md").write_text(summary, encoding="utf-8")
    console.print(summary)
    console.print(f"\n明细：{out / 'details.csv'}")


@app.command()
def version():
    """显示版本。"""
    console.print(f"gewu {gewu.__version__}")


if __name__ == "__main__":
    app()
