from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.auth import TelegramAuthPayload
from app.schemas.movie import MovieRecommendation


class WatchlistAddRequest(TelegramAuthPayload):
    tmdb_id: int
    movie: MovieRecommendation | None = None


class WatchlistItemResponse(BaseModel):
    id: UUID
    user_id: int
    tmdb_id: int
    added_at: datetime
    original_title: str | None = None
    year: int | None = None
    poster_path: str | None = None
    vote_average: float | None = None
    overview: str | None = None
    genre_ids: list[int] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    runtime_minutes: int | None = None
    origin_countries: list[str] = Field(default_factory=list)
    reason_ru: str | None = None
    match_summary_ru: str | None = None
