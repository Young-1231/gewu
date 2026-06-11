"""数字溯源审计（确定性，无 LLM）：研报正文中的每个实质性数字，必须能在
agent 实际看到的数据上下文里找到出处，否则计为「不可溯源」。

这直接针对 LLM 投研最常见的失败模式——幻觉数字。审计结果（溯源率 +
不可溯源清单）作为附录写进每份研报，而不是事后口头保证。

匹配规则：
- 单位归一：``1.6亿`` 与 ``16000万`` 均展开为绝对值参与匹配；
- 舍入感知：报告写 ``6.5%``、上下文为 ``6.54`` 时按报告的小数位舍入比对；
- 相对容差 0.5%。
注意：分析师被要求「不得换算口径」，因此换算产生的数字会被如实标记。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

UNIT_MULTIPLIERS = {"万亿": 1e12, "亿": 1e8, "万": 1e4}
MATERIAL_SUFFIXES = ("%", "元", "倍", "亿", "万", "手", "股", "点")
REL_TOLERANCE = 0.005

# 不排除前置负号：按绝对值匹配（"-9.75" 与上下文 "-9.75" 都提取为 9.75），
# 否则负数会整体逃过审计
_NUMBER = re.compile(r"(?<![A-Za-z0-9_.])(\d+(?:\.\d+)?)(万亿|亿|万)?")
_DATE_LIKE = re.compile(r"\d{4}[-/年]\d{1,2}[-/月]?(?:\d{1,2}日?)?")
_INDEX_NAME_PREFIX = ("沪深", "中证", "科创", "创业板", "上证", "深证", "国证")

AUDIT_START = "<!--audit:start-->"
AUDIT_END = "<!--audit:end-->"


@dataclass
class GroundingResult:
    total: int = 0
    grounded: int = 0
    ungrounded: list[dict] = field(default_factory=list)

    @property
    def rate(self) -> float | None:
        return self.grounded / self.total if self.total else None

    def to_markdown(self) -> str:
        if self.total == 0:
            return "## 数字溯源审计\n\n正文未引用实质性数字。\n"
        lines = [
            "## 数字溯源审计",
            "",
            f"- 实质性数字总数：**{self.total}**",
            f"- 可溯源至数据上下文：**{self.grounded}**（溯源率 **{self.rate:.1%}**）",
        ]
        if self.ungrounded:
            lines += ["- ⚠️ 以下数字无法在数据上下文中找到出处，使用前请人工核验：", ""]
            lines += [
                f"  - `{item['text']}` —— …{item['context']}…" for item in self.ungrounded[:20]
            ]
        else:
            lines.append("- ✅ 全部数字可溯源。")
        return "\n".join(lines) + "\n"


def _decimals(text: str) -> int:
    return len(text.split(".")[1]) if "." in text else 0


def _extract(text: str, *, material_only: bool) -> list[dict]:
    cleaned = _DATE_LIKE.sub(" ", text)
    out = []
    for match in _NUMBER.finditer(cleaned):
        raw_text, unit = match.group(1), match.group(2)
        value = float(raw_text)
        prefix = cleaned[max(0, match.start() - 3) : match.start()]
        suffix = cleaned[match.end() : match.end() + 1]

        if any(prefix.endswith(p) for p in _INDEX_NAME_PREFIX):
            continue  # 沪深300 等指数名
        if (
            not unit
            and "." not in raw_text
            and 1990 <= value <= 2035
            and (suffix.strip() in ("年", "") or suffix in ("Q", "q", "H"))
        ):
            continue  # 年份（含 "2026Q1"、"2025H1" 等报告期写法）
        if material_only:
            material = (
                "." in raw_text
                or unit is not None
                or suffix in MATERIAL_SUFFIXES
                or value >= 100
            )
            if not material:
                continue  # 叙述性小整数（"近20日"、"2-3条"）

        variants = {value}
        if unit:
            variants.add(value * UNIT_MULTIPLIERS[unit])
        out.append(
            {
                "text": raw_text + (unit or "") + (suffix if suffix in MATERIAL_SUFFIXES else ""),
                "value": value,
                "variants": variants,
                "decimals": _decimals(raw_text),
                "context": re.sub(r"\s+", " ", cleaned[max(0, match.start() - 18) : match.end() + 18]).strip(),
            }
        )
    return out


def _is_grounded(item: dict, corpus_values: list[float]) -> bool:
    for report_value in item["variants"]:
        for corpus_value in corpus_values:
            if report_value == corpus_value:
                return True
            if corpus_value != 0 and abs(report_value - corpus_value) / abs(corpus_value) <= REL_TOLERANCE:
                return True
            if round(corpus_value, item["decimals"]) == report_value:
                return True
    return False


def audit(report_text: str, corpus: str) -> GroundingResult:
    """report_text：研报中标记为可审计的正文区域；corpus：agent 看到的全部数据上下文。"""
    corpus_values: list[float] = []
    for item in _extract(corpus, material_only=False):
        corpus_values.extend(item["variants"])

    result = GroundingResult()
    for item in _extract(report_text, material_only=True):
        result.total += 1
        if _is_grounded(item, corpus_values):
            result.grounded += 1
        else:
            result.ungrounded.append({"text": item["text"], "context": item["context"]})
    return result


def extract_audit_region(report_md: str) -> str:
    start = report_md.find(AUDIT_START)
    end = report_md.find(AUDIT_END)
    if start == -1 or end == -1:
        return report_md
    return report_md[start + len(AUDIT_START) : end]
