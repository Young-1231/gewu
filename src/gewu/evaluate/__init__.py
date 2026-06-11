"""评测模块：防泄漏的 Point-in-Time 走查回测 + 基线对照。

设计依据（见 docs/research）：FINSABER（KDD 2026）证明该领域常见的
短窗口、窄股票池回测会因幸存者偏差与数据窥探偏差系统性高估 LLM 策略，
且 LLM 投研存在「牛市过度保守、熊市过度激进」的失败模式。
因此本模块坚持：
1. agent 在每个评测时点只能看到 PIT 数据（与生产路径同一份代码）；
2. 永远与朴素基线（动量、买入持有）同panel对照；
3. 结果报告自带局限性声明，不宣称"显著盈利能力"。
"""

from gewu.evaluate.backtest import run_backtest

__all__ = ["run_backtest"]
