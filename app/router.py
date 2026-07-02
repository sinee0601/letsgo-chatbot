from fastapi import APIRouter, HTTPException

from app.cacheability import is_self_contained
from app.config import settings
from app.embeddings import embed_text
from app.gemini import generate_response
from app.repository import (
    delete_chat_log,
    delete_session,
    get_cached_response,
    get_chat_log_by_id,
    get_chat_logs,
    get_session_history,
    save_chat_log,
    session_has_history,
    upsert_cache,
)
from app.schemas import ChatLogList, ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # 맥락 의존 후속 질문("아까 거 말고" 등)은 공유 캐시를 조회/저장하지 않는다.
    has_history = await session_has_history(request.session_id)
    cacheable = is_self_contained(request.message, has_history)

    # 임베딩/벡터검색 실패는 캐시만 건너뛰고 정상 생성으로 폴백한다.
    embedding = None
    cached = None
    if cacheable:
        try:
            embedding = await embed_text(request.message)
            cached = await get_cached_response(embedding)
        except Exception:
            embedding = None

    if cached is not None:
        bot_response = cached
        model = "cached"
    else:
        if has_history:
            history_logs = await get_session_history(request.session_id)
            history = [
                {"user_message": log["user_message"], "bot_response": log["bot_response"]}
                for log in history_logs
            ]
        else:
            history = []
        try:
            bot_response = await generate_response(request.message, history)
        except Exception:
            raise HTTPException(status_code=429, detail="gemini 서버에러")

        model = settings.gemini_model
        if cacheable and embedding is not None and bot_response:
            try:
                await upsert_cache(embedding, bot_response)
            except Exception:
                pass

    log = await save_chat_log(
        request.session_id, request.message, bot_response, model
    )
    return log


@router.get("", response_model=ChatLogList)
async def list_chats(
    skip: int = 0,
    limit: int = 20,
    session_id: str | None = None,
):
    if limit > 100:
        raise HTTPException(status_code=400, detail="limit은 최대 100")
    total, logs = await get_chat_logs(skip, limit, session_id)
    return ChatLogList(total=total, logs=logs)


@router.get("/{log_id}", response_model=ChatResponse)
async def get_chat(log_id: str):
    log = await get_chat_log_by_id(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="해당 로그 없음")
    return log


@router.delete("/session/{session_id}", status_code=200)
async def delete_session_route(session_id: str):
    count = await delete_session(session_id)
    return {"deleted": count, "session_id": session_id}


@router.delete("/{log_id}", status_code=204)
async def delete_chat(log_id: str):
    deleted = await delete_chat_log(log_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="해당 로그 없음")
