import uuid
from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId
from redis.commands.search.query import Query

from app.config import settings
from app.database import CACHE_INDEX, CACHE_PREFIX, chat_logs_collection, redis_client


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


async def session_has_history(session_id: str) -> bool:
    doc = await chat_logs_collection.find_one(
        {"session_id": session_id}, projection={"_id": 1}
    )
    return doc is not None


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


async def get_cached_response(embedding: bytes) -> str | None:
    """임베딩 벡터로 가장 가까운 캐시를 찾아, 유사도가 임계값 이상이면 답변을 반환한다."""
    query = (
        Query("*=>[KNN 1 @embedding $vec AS distance]")
        .sort_by("distance")
        .return_fields("response", "distance")
        .dialect(2)
    )
    result = await redis_client.ft(CACHE_INDEX).search(
        query, query_params={"vec": embedding}
    )
    if not result.docs:
        return None

    # COSINE distance = 1 - cosine similarity. 거리가 작을수록 의미가 가깝다.
    max_distance = 1 - settings.cache_similarity_threshold
    top = result.docs[0]
    if float(top.distance) <= max_distance:
        return top.response
    return None


async def upsert_cache(embedding: bytes, cached_response: str) -> None:
    key = f"{CACHE_PREFIX}{uuid.uuid4().hex}"
    await redis_client.hset(
        key, mapping={"embedding": embedding, "response": cached_response}
    )
    await redis_client.expire(key, settings.keyword_cache_ttl)
