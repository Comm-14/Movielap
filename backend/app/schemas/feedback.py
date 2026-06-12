from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.auth import TelegramAuthPayload


class MovieFeedbackCreateRequest(TelegramAuthPayload):
    tmdb_id: int
    status: str


class MovieFeedbackResponse(BaseModel):
    id: UUID
    user_id: int
    tmdb_id: int
    status: str
    created_at: datetime
