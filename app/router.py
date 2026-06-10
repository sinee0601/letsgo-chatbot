from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.gemini import generate_response
from app.keywords import extract_keywords
from app.repository import (
    delete_chat_log,
    delete_session,
    get_cached_response,
    get_chat_log_by_id,
    get_chat_logs,
    get_session_history,
    save_chat_log,
    upsert_cache,
)
from app.schemas import ChatLogList, ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    keywords = extract_keywords(request.message)
    cached = await get_cached_response(db, keywords) if keywords else None

    if cached is not None:
        bot_response = cached
        model = "cached"
    else:
        history_logs = await get_session_history(db, request.session_id)
        history = [
            {"user_message": log.user_message, "bot_response": log.bot_response}
            for log in history_logs
        ]
        # try:
        bot_response = await generate_response(request.message, history)
        # except:
        #     raise HTTPException(status_code=429, detail="gemini 서버에러")
            
        model = settings.gemini_model
        if keywords:
            await upsert_cache(db, keywords, bot_response)

    log = await save_chat_log(
        db, request.session_id, request.message, bot_response, model
    )
    return log


@router.get("", response_model=ChatLogList)
async def list_chats(
    skip: int = 0,
    limit: int = 20,
    session_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    if limit > 100:
        raise HTTPException(status_code=400, detail="limit은 최대 100")
    total, logs = await get_chat_logs(db, skip, limit, session_id)
    return ChatLogList(total=total, logs=logs)


@router.get("/{log_id}", response_model=ChatResponse)
async def get_chat(log_id: int, db: AsyncSession = Depends(get_db)):
    log = await get_chat_log_by_id(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="해당 로그 없음")
    return log


@router.delete("/session/{session_id}", status_code=200)
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    count = await delete_session(db, session_id)
    return {"deleted": count, "session_id": session_id}


@router.delete("/{log_id}", status_code=204)
async def delete_chat(log_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await delete_chat_log(db, log_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="해당 로그 없음")
