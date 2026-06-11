"""金融多选题基准跑分 harness（FinEval 兼容格式）。

出于许可证考虑，本仓库**不分发** FinEval 等基准的题目数据，只提供跑分框架与
一份自写的格式样例（data/benchmark_sample.jsonl）。获取真实基准：
FinEval（上财，NAACL 2025）→ https://github.com/SUFE-AIFLM-Lab/FinEval

格式（jsonl 每行一题 / csv 同名列）：
    {"id": "1", "category": "银行", "question": "...", "A": "...", "B": "...",
     "C": "...", "D": "...", "answer": "B"}
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from gewu.llm import LLM

logger = logging.getLogger(__name__)

SYSTEM = "你是金融领域考试作答助手。只输出最终选项字母（A、B、C 或 D），不要输出任何解释。"

_LETTER = re.compile(r"[ABCD]")


@dataclass
class BenchmarkResult:
    total: int = 0
    correct: int = 0
    by_category: dict = field(default_factory=dict)

    @property
    def accuracy(self) -> float | None:
        return self.correct / self.total if self.total else None

    def to_markdown(self, source: str) -> str:
        lines = [
            "## 金融基准跑分",
            "",
            f"- 题集：{source}",
            f"- 总题数：{self.total}，答对：{self.correct}"
            + (f"，准确率：**{self.accuracy:.1%}**" if self.accuracy is not None else ""),
        ]
        if self.by_category:
            lines += ["", "| 类别 | 题数 | 准确率 |", "|---|---|---|"]
            for category, stats in sorted(self.by_category.items()):
                lines.append(f"| {category} | {stats['total']} | {stats['correct'] / stats['total']:.1%} |")
        lines += [
            "",
            "> 注意：多选题准确率衡量的是底座 LLM 的金融知识，不等于 agent 系统的端到端能力；"
            "agent 级评测见 PIT 回测（`gewu backtest`）与数字溯源审计。",
        ]
        return "\n".join(lines)


def load_questions(path: Path) -> list[dict]:
    if path.suffix == ".jsonl":
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    elif path.suffix == ".csv":
        rows = pd.read_csv(path).to_dict("records")
    else:
        raise ValueError("仅支持 .jsonl / .csv 题集")
    questions = []
    for row in rows:
        missing = [key for key in ("question", "A", "B", "C", "D", "answer") if key not in row]
        if missing:
            raise ValueError(f"题目缺少字段 {missing}: {str(row)[:80]}")
        questions.append(row)
    return questions


def _extract_choice(text: str) -> str | None:
    match = _LETTER.search(text.upper())
    return match.group(0) if match else None


def run_benchmark(
    llm: LLM,
    questions: list[dict],
    limit: int | None = None,
    on_event: Callable[[str], None] | None = None,
) -> tuple[pd.DataFrame, BenchmarkResult]:
    emit = on_event or (lambda message: logger.info(message))
    subset = questions[:limit] if limit else questions
    result = BenchmarkResult()
    rows = []
    for index, item in enumerate(subset, start=1):
        user = (
            f"{item['question']}\n"
            f"A. {item['A']}\nB. {item['B']}\nC. {item['C']}\nD. {item['D']}\n只输出选项字母。"
        )
        try:
            raw = llm.complete(SYSTEM, user)
            predicted = _extract_choice(raw)
        except Exception as error:
            logger.warning("第 %d 题调用失败: %s", index, error)
            raw, predicted = f"<error: {error}>", None
        expected = str(item["answer"]).strip().upper()
        is_correct = predicted == expected
        result.total += 1
        result.correct += int(is_correct)
        category = str(item.get("category", "未分类"))
        stats = result.by_category.setdefault(category, {"total": 0, "correct": 0})
        stats["total"] += 1
        stats["correct"] += int(is_correct)
        rows.append(
            {
                "id": item.get("id", index),
                "category": category,
                "expected": expected,
                "predicted": predicted,
                "correct": is_correct,
                "raw": raw[:120],
            }
        )
        emit(f"[{index}/{len(subset)}] {'✓' if is_correct else '✗'} {category}")
    return pd.DataFrame(rows), result
