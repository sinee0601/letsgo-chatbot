from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId

from app.config import settings
from app.database import chat_logs_collection, redis_client


def _serialize_log(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


async def save_chat_log(
    session_id: str,
    user_message: str,
    bot_response: str,
    model: str = settings.gemini_model,
) -> dict:
    doc = {
        "session_id": session_id,
        "user_message": user_message,
        "bot_response": bot_response,
        "model": model,
        "created_at": datetime.utcnow(),
    }
    result = await chat_logs_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _serialize_log(doc)


async def get_session_history(session_id: str, limit: int = 20) -> list[dict]:
    cursor = (
        chat_logs_collection.find({"session_id": session_id})
        .sort("created_at", 1)
        .limit(limit)
    )
    return [_serialize_log(doc) async for doc in cursor]


async def get_chat_logs(
    skip: int = 0,
    limit: int = 20,
    session_id: str | None = None,
) -> tuple[int, list[dict]]:
    query = {"session_id": session_id} if session_id else {}

    total = await chat_logs_collection.count_documents(query)
    cursor = (
        chat_logs_collection.find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    logs = [_serialize_log(doc) async for doc in cursor]
    return total, logs


async def get_chat_log_by_id(log_id: str) -> dict | None:
    try:
        object_id = ObjectId(log_id)
    except InvalidId:
        return None
    doc = await chat_logs_collection.find_one({"_id": object_id})
    return _serialize_log(doc) if doc else None


async def delete_chat_log(log_id: str) -> bool:
    try:
        object_id = ObjectId(log_id)
    except InvalidId:
        return False
    result = await chat_logs_collection.delete_one({"_id": object_id})
    return result.deleted_count > 0


async def delete_session(session_id: str) -> int:
    result = await chat_logs_collection.delete_many({"session_id": session_id})
    return result.deleted_count


def _cache_key(keywords: str) -> str:
    return f"kw:{keywords}"


async def get_cached_response(keywords: str) -> str | None:
    return await redis_client.get(_cache_key(keywords))


async def upsert_cache(keywords: str, cached_response: str) -> None:
    await redis_client.set(
        _cache_key(keywords), cached_response, ex=settings.keyword_cache_ttl
    )
