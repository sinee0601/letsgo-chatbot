from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=36)
    message: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    id: str
    session_id: str
    user_message: str
    bot_response: str
    model: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatLogList(BaseModel):
    total: int
    logs: list[ChatResponse]
