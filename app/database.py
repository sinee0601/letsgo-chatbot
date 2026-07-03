import redis.asyncio as redis
from motor.motor_asyncio import AsyncIOMotorClient
from redis.commands.search.field import TextField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.exceptions import ResponseError

from app.config import settings

mongo_client = AsyncIOMotorClient(settings.mongo_url)
mongo_db = mongo_client[settings.mongo_db]
chat_logs_collection = mongo_db["chat_logs"]

# 임베딩(float32 바이너리)을 저장/검색하므로 decode_responses=False 필수.
# True이면 벡터 검색 응답을 UTF-8로 디코딩하려다 UnicodeDecodeError로 실패한다.
redis_client = redis.from_url(settings.redis_url, decode_responses=False)

CACHE_INDEX = "cache_idx"
CACHE_PREFIX = "semcache:"


async def init_indexes():
    await chat_logs_collection.create_index("session_id")
    await chat_logs_collection.create_index("created_at")
    await _init_cache_index()


async def _init_cache_index():
    try:
        await redis_client.ft(CACHE_INDEX).info()
        return
    except ResponseError:
        pass

    await redis_client.ft(CACHE_INDEX).create_index(
        fields=[
            VectorField(
                "embedding",
                "HNSW",
                {
                    "TYPE": "FLOAT32",
                    "DIM": settings.embedding_dim,
                    "DISTANCE_METRIC": "COSINE",
                },
            ),
            TextField("response"),
        ],
        definition=IndexDefinition(
            prefix=[CACHE_PREFIX], index_type=IndexType.HASH
        ),
    )


async def close_connections():
    mongo_client.close()
    await redis_client.aclose()
