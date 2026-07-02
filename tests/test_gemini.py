"""LLM 레이어: generate_response (Gemini 호출은 목으로 대체)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import app.gemini as gemini


async def test_generate_response_without_history(monkeypatch):
    generate = AsyncMock(return_value=SimpleNamespace(text="답변입니다"))
    fake_client = SimpleNamespace(
        aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    )
    monkeypatch.setattr(gemini, "client", fake_client)

    result = await gemini.generate_response("부산 맛집 알려줘")

    assert result == "답변입니다"
    _, kwargs = generate.call_args
    contents = kwargs["contents"]
    assert contents == [{"role": "user", "parts": [{"text": "부산 맛집 알려줘"}]}]


async def test_generate_response_with_history(monkeypatch):
    generate = AsyncMock(return_value=SimpleNamespace(text="이어서 답변"))
    fake_client = SimpleNamespace(
        aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    )
    monkeypatch.setattr(gemini, "client", fake_client)

    history = [{"user_message": "안녕", "bot_response": "네 안녕하세요"}]
    result = await gemini.generate_response("추천 좀", history)

    assert result == "이어서 답변"
    _, kwargs = generate.call_args
    contents = kwargs["contents"]
    # 히스토리(user/model) 2개 + 현재 user 1개 = 3개
    assert len(contents) == 3
    assert contents[0] == {"role": "user", "parts": [{"text": "안녕"}]}
    assert contents[1] == {"role": "model", "parts": [{"text": "네 안녕하세요"}]}
    assert contents[2] == {"role": "user", "parts": [{"text": "추천 좀"}]}
