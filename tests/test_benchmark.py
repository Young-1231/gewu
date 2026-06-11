"""基准跑分 harness（离线，MockLLM）。"""

from pathlib import Path

import pytest

from gewu.evaluate.benchmark import _extract_choice, load_questions, run_benchmark
from gewu.llm import MockLLM

SAMPLE = Path(__file__).parent.parent / "data" / "benchmark_sample.jsonl"


def test_load_sample_questions():
    questions = load_questions(SAMPLE)
    assert len(questions) == 10
    assert all(q["answer"] in "ABCD" for q in questions)


def test_load_rejects_malformed(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"question": "缺选项", "answer": "A"}', encoding="utf-8")
    with pytest.raises(ValueError, match="缺少字段"):
        load_questions(bad)


def test_extract_choice():
    assert _extract_choice("B") == "B"
    assert _extract_choice("答案是 C。") == "C"
    assert _extract_choice("无法判断") is None


def test_run_benchmark_offline():
    questions = load_questions(SAMPLE)
    details, result = run_benchmark(MockLLM(), questions)
    assert result.total == 10
    # MockLLM 恒答 A：样例集没有正确答案为 A 的题 → 0 分，但管线完整出分
    assert result.correct == 0
    assert result.accuracy == 0.0
    assert set(details["predicted"]) == {"A"}
    markdown = result.to_markdown("sample")
    assert "准确率" in markdown and "财务分析" in markdown


def test_run_benchmark_limit():
    questions = load_questions(SAMPLE)
    details, result = run_benchmark(MockLLM(), questions, limit=3)
    assert result.total == 3 and len(details) == 3
