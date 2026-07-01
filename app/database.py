import redis.asyncio as redis
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

mongo_client = AsyncIOMotorClient(settings.mongo_url)
mongo_db = mongo_client[settings.mongo_db]
chat_logs_collection = mongo_db["chat_logs"]

redis_client = redis.from_url(settings.redis_url, decode_responses=True)


async def init_indexes():
    await chat_logs_collection.create_index("session_id")
    await chat_logs_collection.create_index("created_at")


async def close_connections():
    mongo_client.close()
    await redis_client.aclose()
