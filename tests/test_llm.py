"""LLM 工具与 Mock 的行为契约。"""

import json

import pytest

from gewu.agents import prompts
from gewu.config import Settings
from gewu.llm import ChatLLM, MissingAPIKeyError, MockLLM, extract_json


def test_extract_json_plain():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_fenced():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_with_prose():
    assert extract_json('结论如下：{"rating": "中性"} 以上。') == {"rating": "中性"}


def test_mock_distinguishes_bull_and_bear():
    """回归：多空双方提示词互相提及对方角色，必须按角色声明句匹配。"""
    mock = MockLLM()
    bull = mock.complete(prompts.BULL_SYSTEM, "...")
    bear = mock.complete(prompts.BEAR_SYSTEM, "...")
    assert "多头观点" in bull
    assert "空头观点" in bear
    assert bull != bear


def test_mock_echoes_context_numbers():
    mock = MockLLM()
    text = mock.complete(prompts.ANALYST_SYSTEM["technical"], "最新收盘价: 1275.88\n区间涨跌幅: -9.75")
    assert "1275.88" in text


def test_mock_director_json_valid():
    mock = MockLLM()
    decision = json.loads(mock.complete(prompts.DIRECTOR_SYSTEM, "...", json_mode=True))
    assert decision["rating"] in ("买入", "增持", "中性", "减持")


def test_chat_llm_requires_api_key():
    settings = Settings.load(api_key=None)
    settings = type(settings)(**{**settings.__dict__, "api_key": None})
    with pytest.raises(MissingAPIKeyError):
        ChatLLM(settings)
