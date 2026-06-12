from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.auth import TelegramAuthPayload
from app.schemas.filters import HardFilters
from app.schemas.movie import MovieRecommendation


class SessionCreateRequest(TelegramAuthPayload):
    preference_text: str = Field(min_length=3, max_length=2000)
    moods: list[str] = Field(default_factory=list)
    hard_filters: HardFilters | None = None
    max_participants: int = Field(default=2, ge=2, le=5)


class SessionJoinRequest(TelegramAuthPayload):
    session_id: UUID
    preference_text: str = Field(min_length=3, max_length=2000)
    moods: list[str] = Field(default_factory=list)
    hard_filters: HardFilters | None = None


class SessionResponse(BaseModel):
    id: UUID
    type: str
    status: str
    creator_id: int
    guest_id: int | None = None
    participant_ids: list[int] = Field(default_factory=list)
    max_participants: int = 2
    invite_link: str | None = None
    created_at: datetime
    movies: list[MovieRecommendation] | None = None


class SessionMoviesReadyEvent(BaseModel):
    session_id: UUID
    event: str = "movies_ready"
    movies: list[MovieRecommendation]
