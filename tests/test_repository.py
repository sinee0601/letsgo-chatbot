"""데이터 접근 레이어: repository (MongoDB/Redis는 목으로 대체)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

import app.repository as repo


class FakeCursor:
    """motor 커서의 sort/skip/limit 체이닝과 async 이터레이션을 흉내낸다."""

    def __init__(self, docs):
        self._docs = docs

    def sort(self, *args, **kwargs):
        return self

    def skip(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def __aiter__(self):
        self._it = iter(self._docs)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


# --- MongoDB 계열 -----------------------------------------------------------

async def test_save_chat_log(monkeypatch):
    oid = ObjectId()
    collection = MagicMock()
    collection.insert_one = AsyncMock(return_value=SimpleNamespace(inserted_id=oid))
    monkeypatch.setattr(repo, "chat_logs_collection", collection)

    log = await repo.save_chat_log("s1", "안녕", "네 안녕하세요", "gemini-2.0-flash")

    assert log["id"] == str(oid)
    assert log["session_id"] == "s1"
    assert log["user_message"] == "안녕"
    assert log["bot_response"] == "네 안녕하세요"
    assert log["model"] == "gemini-2.0-flash"
    assert "_id" not in log
    collection.insert_one.assert_awaited_once()


async def test_session_has_history_true(monkeypatch):
    collection = MagicMock()
    collection.find_one = AsyncMock(return_value={"_id": ObjectId()})
    monkeypatch.setattr(repo, "chat_logs_collection", collection)

    assert await repo.session_has_history("s1") is True


async def test_session_has_history_false(monkeypatch):
    collection = MagicMock()
    collection.find_one = AsyncMock(return_value=None)
    monkeypatch.setattr(repo, "chat_logs_collection", collection)

    assert await repo.session_has_history("s1") is False


async def test_get_session_history(monkeypatch):
    docs = [
        {"_id": ObjectId(), "session_id": "s1", "user_message": "q1", "bot_response": "a1"},
        {"_id": ObjectId(), "session_id": "s1", "user_message": "q2", "bot_response": "a2"},
    ]
    collection = MagicMock()
    collection.find = MagicMock(return_value=FakeCursor(docs))
    monkeypatch.setattr(repo, "chat_logs_collection", collection)

    logs = await repo.get_session_history("s1")

    assert len(logs) == 2
    assert all("id" in log and "_id" not in log for log in logs)


async def test_get_chat_logs(monkeypatch):
    docs = [{"_id": ObjectId(), "session_id": "s1", "user_message": "q", "bot_response": "a"}]
    collection = MagicMock()
    collection.count_documents = AsyncMock(return_value=1)
    collection.find = MagicMock(return_value=FakeCursor(docs))
    monkeypatch.setattr(repo, "chat_logs_collection", collection)

    total, logs = await repo.get_chat_logs(skip=0, limit=20, session_id="s1")

    assert total == 1
    assert len(logs) == 1
    collection.count_documents.assert_awaited_once_with({"session_id": "s1"})


async def test_get_chat_log_by_id_found(monkeypatch):
    oid = ObjectId()
    collection = MagicMock()
    collection.find_one = AsyncMock(
        return_value={"_id": oid, "session_id": "s1", "user_message": "q", "bot_response": "a"}
    )
    monkeypatch.setattr(repo, "chat_logs_collection", collection)

    log = await repo.get_chat_log_by_id(str(oid))
    assert log["id"] == str(oid)


async def test_get_chat_log_by_id_invalid():
    # 잘못된 ObjectId 형식이면 DB 접근 없이 None 반환.
    assert await repo.get_chat_log_by_id("not-an-object-id") is None


async def test_delete_chat_log(monkeypatch):
    oid = ObjectId()
    collection = MagicMock()
    collection.delete_one = AsyncMock(return_value=SimpleNamespace(deleted_count=1))
    monkeypatch.setattr(repo, "chat_logs_collection", collection)

    assert await repo.delete_chat_log(str(oid)) is True


async def test_delete_chat_log_invalid():
    assert await repo.delete_chat_log("bad-id") is False


async def test_delete_session(monkeypatch):
    collection = MagicMock()
    collection.delete_many = AsyncMock(return_value=SimpleNamespace(deleted_count=3))
    monkeypatch.setattr(repo, "chat_logs_collection", collection)

    assert await repo.delete_session("s1") == 3


# --- Redis 시맨틱 캐시 계열 --------------------------------------------------

def _redis_with_search(docs):
    ft = MagicMock()
    ft.search = AsyncMock(return_value=SimpleNamespace(docs=docs))
    redis_mock = MagicMock()
    redis_mock.ft = MagicMock(return_value=ft)
    return redis_mock, ft


async def test_get_cached_response_hit(monkeypatch):
    # distance 0.05 <= max_distance(1 - 0.92 = 0.08) → 히트
    doc = SimpleNamespace(response="캐시된 답변", distance="0.05")
    redis_mock, ft = _redis_with_search([doc])
    monkeypatch.setattr(repo, "redis_client", redis_mock)

    result = await repo.get_cached_response(b"\x00" * 16)

    assert result == "캐시된 답변"
    ft.search.assert_awaited_once()


async def test_get_cached_response_below_threshold(monkeypatch):
    # distance 0.5 > 0.08 → 유사도 부족, 미스 처리
    doc = SimpleNamespace(response="너무 먼 답변", distance="0.5")
    redis_mock, _ = _redis_with_search([doc])
    monkeypatch.setattr(repo, "redis_client", redis_mock)

    assert await repo.get_cached_response(b"\x00" * 16) is None


async def test_get_cached_response_empty(monkeypatch):
    redis_mock, _ = _redis_with_search([])
    monkeypatch.setattr(repo, "redis_client", redis_mock)

    assert await repo.get_cached_response(b"\x00" * 16) is None


async def test_upsert_cache(monkeypatch):
    redis_mock = MagicMock()
    redis_mock.hset = AsyncMock()
    redis_mock.expire = AsyncMock()
    monkeypatch.setattr(repo, "redis_client", redis_mock)

    await repo.upsert_cache(b"vec-bytes", "저장할 답변")

    redis_mock.hset.assert_awaited_once()
    args, kwargs = redis_mock.hset.call_args
    key = args[0]
    assert key.startswith(repo.CACHE_PREFIX)
    assert kwargs["mapping"]["embedding"] == b"vec-bytes"
    assert kwargs["mapping"]["response"] == "저장할 답변"
    redis_mock.expire.assert_awaited_once()
