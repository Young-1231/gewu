"""数字溯源审计的行为契约。"""

from gewu.agents.fact_check import audit

CORPUS = """
- 最新收盘价: 1275.88
- 区间涨跌幅: -9.75
- PE(TTM): 19.28
- 营业收入同比: 6.54
- 总市值: 15949.5亿元
近10个交易日收盘价
 2026-06-10 1275.88
"""


def test_grounded_numbers_pass():
    report = "最新收盘价 1275.88 元，PE(TTM) 19.28 倍，营收同比增长 6.54%。"
    result = audit(report, CORPUS)
    assert result.total == 3
    assert result.grounded == 3
    assert result.rate == 1.0


def test_fabricated_number_flagged():
    report = "公司净利润率高达 88.66%，收盘价 1275.88 元。"
    result = audit(report, CORPUS)
    assert result.total == 2
    assert result.grounded == 1
    assert result.ungrounded[0]["text"].startswith("88.66")


def test_rounding_tolerance():
    # 上下文 6.54 → 报告写 6.5（按报告小数位舍入比对）
    result = audit("营收同比约 6.5%。", CORPUS)
    assert result.grounded == 1


def test_unit_expansion():
    # 15949.5（亿）≈ 1.59 万亿：换算口径在容差内可溯源
    result = audit("总市值约 1.59万亿 元。", CORPUS)
    assert result.grounded == 1


def test_negative_numbers_matched_by_magnitude():
    result = audit("区间涨跌幅 -9.75%，明显弱于大盘。", CORPUS)
    assert result.total == 1
    assert result.grounded == 1


def test_years_dates_index_names_skipped():
    report = "2025 年以来，公司在 2025-04-15 发布公告；沪深300 同期上涨。表现见第 3 节。2026Q1 与 2025H1 业绩企稳。"
    result = audit(report, CORPUS)
    assert result.total == 0  # 年份/日期/报告期/指数名/叙述性小整数都不算实质性数字


def test_empty_report():
    result = audit("公司基本面稳健，无重大变化。", CORPUS)
    assert result.total == 0
    assert result.rate is None
    assert "未引用实质性数字" in result.to_markdown()
