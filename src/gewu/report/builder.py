"""把图状态装配成中文研报 markdown。

LLM 生成的内容被 ``<!--audit:start/end-->`` 标记包裹——只有这部分参与
数字溯源审计；元数据（评级、来源表等）由代码生成，不在审计范围。
"""

from __future__ import annotations

from gewu.agents.fact_check import AUDIT_END, AUDIT_START
from gewu.agents.prompts import ANALYST_TITLES
from gewu.agents.state import ResearchState
from gewu.data.bundle import DataBundle

_RATING_BADGES = {"买入": "🟥 买入", "增持": "🟧 增持", "中性": "⬜ 中性", "减持": "🟦 减持"}

DISCLAIMER = (
    "本报告由开源项目「格物 Gewu」的多智能体系统自动生成，仅用于技术演示与研究，"
    "不构成任何投资建议。AI 生成内容可能存在错误；数字溯源审计仅验证数字出处，"
    "不验证观点正确性。市场有风险，投资需谨慎。"
)


def build_report(
    bundle: DataBundle,
    state: ResearchState,
    charts: list[tuple[str, str]] | None = None,
) -> str:
    decision = state.get("decision", {})
    rating = decision.get("rating", "中性")
    confidence = decision.get("confidence", 0.0)
    reports = state.get("analyst_reports", {})

    lines: list[str] = [
        f"# {bundle.name}（{bundle.symbol}）研究报告",
        "",
        f"> 评级：**{_RATING_BADGES.get(rating, rating)}** ｜ 置信度：{confidence:.0%} ｜ "
        f"分析基准日：{bundle.as_of} ｜ 引擎：格物 Gewu 多智能体",
        "",
        AUDIT_START,
        "## 投资要点",
        "",
        decision.get("summary", "（无裁决摘要）"),
        "",
    ]
    lines += [f"- {point}" for point in decision.get("key_points", [])]

    lines += ["", "## 分析师观点", ""]
    for role, title in ANALYST_TITLES.items():
        if role in reports:
            lines += [f"### {title}", "", reports[role], ""]

    debate = state.get("debate", [])
    if debate:
        lines += ["## 多空辩论纪要", ""]
        for entry in debate:
            side = "🐂 多头" if entry["role"] == "bull" else "🐻 空头"
            lines += [f"**{side}（第{entry['round']}轮）**：{entry['content']}", ""]

    risks = decision.get("risks", [])
    if risks:
        lines += ["## 风险提示", ""]
        lines += [f"- {risk}" for risk in risks]
    lines += ["", AUDIT_END, ""]

    if charts:
        lines += ["## 图表", ""]
        lines += [f"![{title}]({path})" for title, path in charts]
        lines.append("")

    lines += ["## 数据与方法", ""]
    lines.append(f"- 数据源：{'、'.join(f'{k}={v}' for k, v in bundle.sources.items()) or '无'}")
    lines.append(
        f"- Point-in-Time：所有数据截断至 {bundle.as_of}；财报按法定披露截止日判定可见性（保守、零泄漏）"
    )
    for warning in bundle.warnings:
        lines.append(f"- ⚠️ {warning}")
    lines += ["", "## 免责声明", "", DISCLAIMER, ""]
    return "\n".join(lines)
