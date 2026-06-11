"""LLM 客户端：OpenAI 兼容接口（默认 DeepSeek）+ 离线 Mock 实现。

所有 agent 通过统一的 ``LLM`` 协议调用模型，因此换模型 = 换 base_url/model 两个配置。
"""

from __future__ import annotations

import json
import re
import time
from typing import Protocol

from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

from gewu.config import Settings

_RETRYABLE = (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError)


class MissingAPIKeyError(RuntimeError):
    pass


class LLM(Protocol):
    def complete(self, system: str, user: str, *, json_mode: bool = False) -> str: ...


class ChatLLM:
    """同步 OpenAI 兼容客户端，带指数退避重试。"""

    def __init__(self, settings: Settings, max_retries: int = 3, timeout: float = 180.0):
        if not settings.api_key:
            raise MissingAPIKeyError(
                "未找到 API key。请设置 GEWU_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY，"
                "或使用 --mock 离线模式。"
            )
        self.model = settings.model
        self.temperature = settings.temperature
        self.max_retries = max_retries
        self._client = OpenAI(api_key=settings.api_key, base_url=settings.base_url, timeout=timeout)

    def complete(self, system: str, user: str, *, json_mode: bool = False) -> str:
        kwargs: dict = {}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=self.temperature,
                    **kwargs,
                )
                return response.choices[0].message.content or ""
            except _RETRYABLE as error:
                last_error = error
                if attempt < self.max_retries:
                    time.sleep(min(2.0 * 2**attempt, 30.0))
        raise RuntimeError(f"LLM 调用在 {self.max_retries + 1} 次尝试后仍失败") from last_error


_MOCK_NOTE = "（Mock 模式输出，仅用于离线演示与测试，不代表真实模型分析。）"

_MOCK_FIELD_PATTERN = re.compile(
    r"(最新收盘价|区间涨跌幅|PE\(TTM\)|市净率|总市值|营业收入同比|归母净利润同比)[:：]\s*(-?[\d.]+)"
)


class MockLLM:
    """离线确定性 Mock：按角色返回模板文本，并回显数据上下文中的真实数字。

    回显数字使得「数字溯源审计」在 mock 模式下也能验证完整链路。
    """

    def complete(self, system: str, user: str, *, json_mode: bool = False) -> str:
        facts = {m.group(1): m.group(2) for m in _MOCK_FIELD_PATTERN.finditer(user)}

        def fact_line(label: str, suffix: str = "") -> str:
            return f"{label} {facts[label]}{suffix}" if label in facts else ""

        if json_mode:
            return json.dumps(
                {
                    "rating": "中性",
                    "confidence": 0.5,
                    "summary": f"综合多空观点后给出中性评级。{_MOCK_NOTE}",
                    "key_points": [
                        "基本面与估值信号相互抵消，缺乏单边驱动。",
                        "技术面未出现明确趋势确认。",
                    ],
                    "risks": ["宏观与行业政策不确定性", "数据覆盖窗口有限"],
                },
                ensure_ascii=False,
            )
        if "考试作答助手" in system:
            return "A"
        if "公告问答助手" in system:
            number = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(万元|亿元|元|%)", user)
            quoted = f"{number.group(1)}{number.group(2)}" if number else "（片段中无数字）"
            return f"根据公告片段，相关数值为 {quoted}（来源见片段标注）。{_MOCK_NOTE}"
        if "基本面分析师" in system:
            lines = [x for x in (fact_line("营业收入同比", "%"), fact_line("归母净利润同比", "%")) if x]
            detail = "；".join(lines) if lines else "财务数据见数据上下文"
            return f"## 基本面观察\n\n公司近期财务表现：{detail}。盈利质量与成长趋势需结合行业景气判断。\n\n{_MOCK_NOTE}"
        if "技术面分析师" in system:
            lines = [x for x in (fact_line("最新收盘价", " 元"), fact_line("区间涨跌幅", "%")) if x]
            detail = "；".join(lines) if lines else "价格走势见数据上下文"
            return f"## 技术面观察\n\n{detail}。均线系统与动量指标未给出一致信号。\n\n{_MOCK_NOTE}"
        if "舆情" in system or "新闻" in system:
            return f"## 舆情观察\n\n近期公开新闻以中性事件为主，未发现重大利好或利空催化。\n\n{_MOCK_NOTE}"
        if "行业横向对比分析师" in system:
            return f"## 行业对比观察\n\n目标公司估值相对同行处于可比区间，溢价与基本面差异大体匹配。\n\n{_MOCK_NOTE}"
        if "估值分析师" in system:
            lines = [x for x in (fact_line("PE(TTM)", " 倍"), fact_line("市净率", " 倍")) if x]
            detail = "；".join(lines) if lines else "估值数据见数据上下文"
            return f"## 估值观察\n\n当前估值水平：{detail}。相对历史分位的吸引力一般。\n\n{_MOCK_NOTE}"
        # 多空双方的提示词都同时提到"多头研究员/空头研究员"（要求反驳对方），
        # 必须匹配角色声明句而非裸关键词
        if "你是研究团队中的多头研究员" in system:
            return f"多头观点：基本面稳健且估值未泡沫化，回调即是配置机会。{_MOCK_NOTE}"
        if "你是研究团队中的空头研究员" in system:
            return f"空头观点：增长动能边际放缓，估值缺乏进一步扩张的催化。{_MOCK_NOTE}"
        return f"分析意见：信息不足以形成强观点。{_MOCK_NOTE}"


def extract_json(text: str) -> dict:
    """容错解析 LLM 返回的 JSON：剥 ```json 围栏，退化到首个 {...} 块。"""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def build_llm(settings: Settings, mock: bool = False) -> LLM:
    return MockLLM() if mock else ChatLLM(settings)
