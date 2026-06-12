from uuid import UUID

from pydantic import BaseModel

from app.schemas.auth import TelegramAuthPayload
from app.schemas.movie import MovieRecommendation


class SwipeCreateRequest(TelegramAuthPayload):
    session_id: UUID
    tmdb_id: int
    action: str


class SwipeResponse(BaseModel):
    matched: bool
    movie: MovieRecommendation | None = None
