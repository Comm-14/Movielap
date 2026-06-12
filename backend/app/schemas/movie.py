from pydantic import BaseModel, Field


class MatchExplainerItem(BaseModel):
    audience_label: str
    reason_ru: str


class StreamingProvider(BaseModel):
    name: str


class MovieRecommendation(BaseModel):
    tmdb_id: int
    original_title: str
    year: int | None = None
    poster_path: str | None = None
    vote_average: float | None = None
    overview: str | None = None
    genre_ids: list[int] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    runtime_minutes: int | None = None
    origin_countries: list[str] = Field(default_factory=list)
    reason_ru: str
    match_summary_ru: str | None = None
    match_explainer: list[MatchExplainerItem] = Field(default_factory=list)
    trailer_url: str | None = None
    streaming_providers: list[StreamingProvider] = Field(default_factory=list)


class GeminiMovieCandidate(BaseModel):
    original_title: str
    year: int | None = None
    reason_ru: str
    match_summary_ru: str | None = None
    match_explainer: list[MatchExplainerItem] = Field(default_factory=list)


class GeminiRecommendationPayload(BaseModel):
    movies: list[GeminiMovieCandidate]
