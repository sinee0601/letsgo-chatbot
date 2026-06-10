from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import ChatLog, KeywordCache


async def save_chat_log(
    db: AsyncSession,
    session_id: str,
    user_message: str,
    bot_response: str,
    model: str = settings.gemini_model,
) -> ChatLog:
    log = ChatLog(
        session_id=session_id,
        user_message=user_message,
        bot_response=bot_response,
        model=model,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def get_session_history(
    db: AsyncSession,
    session_id: str,
    limit: int = 20
) -> list[ChatLog]:
    result = await db.execute(
        select(ChatLog)
        .where(ChatLog.session_id == session_id)
        .order_by(ChatLog.created_at.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_chat_logs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    session_id: str | None = None
) -> tuple[int, list[ChatLog]]:
    base_query = select(ChatLog)
    count_query = select(func.count()).select_from(ChatLog)

    if session_id:
        base_query = base_query.where(ChatLog.session_id == session_id)
        count_query = count_query.where(ChatLog.session_id == session_id)

    total = (await db.execute(count_query)).scalar_one()
    logs = list(
        (
            await db.execute(
                base_query.order_by(ChatLog.created_at.desc()).offset(skip).limit(limit)
            )
        ).scalars().all()
    )
    return total, logs


async def get_chat_log_by_id(db: AsyncSession, log_id: int) -> ChatLog | None:
    result = await db.execute(select(ChatLog).where(ChatLog.id == log_id))
    return result.scalar_one_or_none()


async def delete_chat_log(db: AsyncSession, log_id: int) -> bool:
    log = await get_chat_log_by_id(db, log_id)
    if not log:
        return False
    await db.delete(log)
    await db.commit()
    return True


async def delete_session(db: AsyncSession, session_id: str) -> int:
    result = await db.execute(
        select(ChatLog).where(ChatLog.session_id == session_id)
    )
    logs = result.scalars().all()
    count = len(logs)
    for log in logs:
        await db.delete(log)
    await db.commit()
    return count

async def get_cached_response(db: AsyncSession, keywords: str) -> str | None:
    result = await db.execute(
        select(KeywordCache.cached_response).where(KeywordCache.keywords == keywords)
    )
    return result.scalar_one_or_none()


async def upsert_cache(db: AsyncSession, keywords: str, cached_response: str) -> None:
    stmt = mysql_insert(KeywordCache).values(
        keywords=keywords, cached_response=cached_response
    )
    stmt = stmt.on_duplicate_key_update(
        cached_response=stmt.inserted.cached_response
    )
    await db.execute(stmt)
    await db.commit()

