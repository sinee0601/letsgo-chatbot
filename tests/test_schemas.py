"""스키마 레이어: pydantic 검증."""
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas import ChatLogList, ChatRequest, ChatResponse


def test_chat_request_valid():
    req = ChatRequest(session_id="s1", message="안녕")
    assert req.session_id == "s1"
    assert req.message == "안녕"


@pytest.mark.parametrize(
    "session_id,message",
    [
        ("", "안녕"),               # session_id 최소 길이 위반
        ("x" * 37, "안녕"),         # session_id 최대 길이 위반
        ("s1", ""),                 # message 최소 길이 위반
        ("s1", "x" * 4001),         # message 최대 길이 위반
    ],
)
def test_chat_request_invalid(session_id, message):
    with pytest.raises(ValidationError):
        ChatRequest(session_id=session_id, message=message)


def test_chat_response_from_dict():
    doc = {
        "id": "abc123",
        "session_id": "s1",
        "user_message": "안녕",
        "bot_response": "네 안녕하세요",
        "model": "gemini-2.0-flash",
        "created_at": datetime(2026, 7, 2, 12, 0, 0),
    }
    resp = ChatResponse(**doc)
    assert resp.id == "abc123"
    assert resp.model == "gemini-2.0-flash"


def test_chat_log_list():
    resp = ChatResponse(
        id="1",
        session_id="s1",
        user_message="q",
        bot_response="a",
        model="cached",
        created_at=datetime(2026, 7, 2),
    )
    listing = ChatLogList(total=1, logs=[resp])
    assert listing.total == 1
    assert len(listing.logs) == 1
