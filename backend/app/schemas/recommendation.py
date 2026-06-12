from pydantic import BaseModel, Field

from app.schemas.auth import TelegramAuthPayload
from app.schemas.filters import HardFilters
from app.schemas.movie import MovieRecommendation


class SoloRecommendationRequest(TelegramAuthPayload):
    preference_text: str = Field(min_length=3, max_length=2000)
    moods: list[str] = Field(default_factory=list)
    hard_filters: HardFilters | None = None


class RecommendationResponse(BaseModel):
    movies: list[MovieRecommendation]
