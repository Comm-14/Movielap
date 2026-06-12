from pydantic import BaseModel, Field


class HardFilters(BaseModel):
    include_genres: list[str] = Field(default_factory=list)
    exclude_genres: list[str] = Field(default_factory=list)
    year_from: int | None = None
    year_to: int | None = None
    countries: list[str] = Field(default_factory=list)
    min_runtime: int | None = None
    max_runtime: int | None = None
    min_rating: float | None = None
    exclude_keywords: list[str] = Field(default_factory=list)
