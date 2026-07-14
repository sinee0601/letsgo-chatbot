"""API 레이어: /chat 라우터 (의존 계층은 목으로 대체).

lifespan(init_indexes)을 피하려고 라우터만 얹은 별도 FastAPI 앱으로 테스트한다.
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.router as router_module
from app.config import settings
from app.router import router


@pytest.fixture
def client():
    test_app = FastAPI()
    test_app.include_router(router)
    return TestClient(test_app)


def _make_log(model, message="부산 맛집", bot="추천 답변"):
    return {
        "id": "log-1",
        "session_id": "s1",
        "user_message": message,
        "bot_response": bot,
        "model": model,
        "created_at": datetime(2026, 7, 2, 12, 0, 0),
    }


def test_chat_cache_hit(client, monkeypatch):
    """자기완결 질문 + 캐시 히트 → Gemini 호출 없이 캐시 사용."""
    monkeypatch.setattr(router_module, "session_has_history", AsyncMock(return_value=False))
    monkeypatch.setattr(router_module, "is_self_contained", MagicMock(return_value=True))
    monkeypatch.setattr(router_module, "embed_text", AsyncMock(return_value=b"vec"))
    monkeypatch.setattr(router_module, "get_cached_response", AsyncMock(return_value="캐시 답변"))
    generate = AsyncMock()
    monkeypatch.setattr(router_module, "generate_response", generate)
    upsert = AsyncMock()
    monkeypatch.setattr(router_module, "upsert_cache", upsert)
    monkeypatch.setattr(
        router_module, "save_chat_log", AsyncMock(return_value=_make_log("cached", bot="캐시 답변"))
    )

    resp = client.post("/chat", json={"session_id": "s1", "message": "부산 맛집"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["model"] == "cached"
    assert body["bot_response"] == "캐시 답변"
    generate.assert_not_awaited()   # 캐시 히트이므로 생성 안 함
    upsert.assert_not_awaited()     # 이미 캐시에 있으므로 저장 안 함


def test_chat_cache_miss_generates_and_caches(client, monkeypatch):
    """캐시 미스 → Gemini 생성 후 캐시에 저장."""
    monkeypatch.setattr(router_module, "session_has_history", AsyncMock(return_value=False))
    monkeypatch.setattr(router_module, "is_self_contained", MagicMock(return_value=True))
    monkeypatch.setattr(router_module, "embed_text", AsyncMock(return_value=b"vec"))
    monkeypatch.setattr(router_module, "get_cached_response", AsyncMock(return_value=None))
    generate = AsyncMock(return_value="새로 생성된 답변")
    monkeypatch.setattr(router_module, "generate_response", generate)
    upsert = AsyncMock()
    monkeypatch.setattr(router_module, "upsert_cache", upsert)
    monkeypatch.setattr(
        router_module,
        "save_chat_log",
        AsyncMock(return_value=_make_log(settings.gemini_model, bot="새로 생성된 답변")),
    )

    resp = client.post("/chat", json={"session_id": "s1", "message": "부산 맛집"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["model"] == settings.gemini_model
    generate.assert_awaited_once()
    upsert.assert_awaited_once()    # 새 답변을 캐시에 저장


def test_chat_follow_up_bypasses_cache(client, monkeypatch):
    """맥락 의존 후속 질문 → 임베딩/캐시 조회·저장 모두 스킵."""
    monkeypatch.setattr(router_module, "session_has_history", AsyncMock(return_value=True))
    monkeypatch.setattr(router_module, "is_self_contained", MagicMock(return_value=False))
    embed = AsyncMock()
    monkeypatch.setattr(router_module, "embed_text", embed)
    get_cached = AsyncMock()
    monkeypatch.setattr(router_module, "get_cached_response", get_cached)
    monkeypatch.setattr(router_module, "get_session_history", AsyncMock(return_value=[]))
    generate = AsyncMock(return_value="맥락 반영 답변")
    monkeypatch.setattr(router_module, "generate_response", generate)
    upsert = AsyncMock()
    monkeypatch.setattr(router_module, "upsert_cache", upsert)
    monkeypatch.setattr(
        router_module,
        "save_chat_log",
        AsyncMock(return_value=_make_log(settings.gemini_model, bot="맥락 반영 답변")),
    )

    resp = client.post("/chat", json={"session_id": "s1", "message": "아까 거 말고"})

    assert resp.status_code == 200
    embed.assert_not_awaited()
    get_cached.assert_not_awaited()
    upsert.assert_not_awaited()
    generate.assert_awaited_once()


def test_chat_gemini_error_returns_429(client, monkeypatch):
    monkeypatch.setattr(router_module, "session_has_history", AsyncMock(return_value=False))
    monkeypatch.setattr(router_module, "is_self_contained", MagicMock(return_value=True))
    monkeypatch.setattr(router_module, "embed_text", AsyncMock(return_value=b"vec"))
    monkeypatch.setattr(router_module, "get_cached_response", AsyncMock(return_value=None))
    monkeypatch.setattr(
        router_module, "generate_response", AsyncMock(side_effect=RuntimeError("boom"))
    )

    resp = client.post("/chat", json={"session_id": "s1", "message": "부산 맛집"})
    assert resp.status_code == 429


def test_chat_request_validation(client):
    # message 빈 문자열 → 422 (pydantic 검증)
    resp = client.post("/chat", json={"session_id": "s1", "message": ""})
    assert resp.status_code == 422


def test_list_chats_limit_over_100(client):
    resp = client.get("/chat", params={"limit": 101})
    assert resp.status_code == 400


def test_list_chats_ok(client, monkeypatch):
    monkeypatch.setattr(
        router_module,
        "get_chat_logs",
        AsyncMock(return_value=(1, [_make_log("cached")])),
    )
    resp = client.get("/chat", params={"limit": 20})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["logs"]) == 1


def test_get_chat_not_found(client, monkeypatch):
    monkeypatch.setattr(router_module, "get_chat_log_by_id", AsyncMock(return_value=None))
    resp = client.get("/chat/64b7f0000000000000000000")
    assert resp.status_code == 404


def test_get_chat_found(client, monkeypatch):
    monkeypatch.setattr(
        router_module, "get_chat_log_by_id", AsyncMock(return_value=_make_log("cached"))
    )
    resp = client.get("/chat/log-1")
    assert resp.status_code == 200
    assert resp.json()["id"] == "log-1"


def test_delete_session(client, monkeypatch):
    monkeypatch.setattr(router_module, "delete_session", AsyncMock(return_value=2))
    resp = client.delete("/chat/session/s1")
    assert resp.status_code == 200
    assert resp.json() == {"deleted": 2, "session_id": "s1"}


def test_delete_chat_not_found(client, monkeypatch):
    monkeypatch.setattr(router_module, "delete_chat_log", AsyncMock(return_value=False))
    resp = client.delete("/chat/64b7f0000000000000000000")
    assert resp.status_code == 404


def test_delete_chat_ok(client, monkeypatch):
    monkeypatch.setattr(router_module, "delete_chat_log", AsyncMock(return_value=True))
    resp = client.delete("/chat/log-1")
    assert resp.status_code == 204
