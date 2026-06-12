from app.schemas.filters import HardFilters
from app.schemas.movie import MovieRecommendation
from app.services.gemini_service import gemini_service
from app.services.tmdb_service import tmdb_service


class RecommendationService:
    async def build_solo_recommendations(
        self,
        preference_text: str,
        *,
        moods: list[str] | None = None,
        hard_filters: HardFilters | None = None,
    ) -> list[MovieRecommendation]:
        gemini_candidates = await gemini_service.recommend_movies(
            preference_text,
            participant_labels=["Тебе"],
            moods=moods,
            hard_filters=hard_filters,
        )
        movies = await tmdb_service.enrich_movies(gemini_candidates)
        return self._apply_hard_filters(movies, hard_filters)

    async def build_group_recommendations(self, participant_profiles: list[dict]) -> list[MovieRecommendation]:
        combined_text = "\n".join(
            f"{profile['label']}: {profile['preference_text']}" for profile in participant_profiles if profile.get("preference_text")
        )
        moods = [mood for profile in participant_profiles for mood in profile.get("moods", [])]
        hard_filters = self._merge_hard_filters([profile.get("hard_filters") for profile in participant_profiles])
        gemini_candidates = await gemini_service.recommend_movies(
            combined_text,
            participant_labels=[str(profile["label"]) for profile in participant_profiles],
            moods=moods,
            hard_filters=hard_filters,
        )
        movies = await tmdb_service.enrich_movies(gemini_candidates)
        return self._apply_hard_filters(movies, hard_filters)

    @staticmethod
    def _merge_hard_filters(filters_list: list[HardFilters | dict | None]) -> HardFilters | None:
        merged = HardFilters()
        has_values = False
        for raw_filters in filters_list:
            if raw_filters is None:
                continue
            filters = raw_filters if isinstance(raw_filters, HardFilters) else HardFilters.model_validate(raw_filters)
            merged.include_genres = sorted(set(merged.include_genres + filters.include_genres))
            merged.exclude_genres = sorted(set(merged.exclude_genres + filters.exclude_genres))
            merged.countries = sorted(set(merged.countries + filters.countries))
            merged.exclude_keywords = sorted(set(merged.exclude_keywords + filters.exclude_keywords))
            merged.year_from = max(filter(lambda item: item is not None, [merged.year_from, filters.year_from]), default=None)
            merged.year_to = min(filter(lambda item: item is not None, [merged.year_to, filters.year_to]), default=None)
            merged.min_runtime = max(filter(lambda item: item is not None, [merged.min_runtime, filters.min_runtime]), default=None)
            merged.max_runtime = min(filter(lambda item: item is not None, [merged.max_runtime, filters.max_runtime]), default=None)
            merged.min_rating = max(filter(lambda item: item is not None, [merged.min_rating, filters.min_rating]), default=None)
            has_values = has_values or any(
                [
                    filters.include_genres,
                    filters.exclude_genres,
                    filters.countries,
                    filters.exclude_keywords,
                    filters.year_from is not None,
                    filters.year_to is not None,
                    filters.min_runtime is not None,
                    filters.max_runtime is not None,
                    filters.min_rating is not None,
                ]
            )
        return merged if has_values else None

    @staticmethod
    def _apply_hard_filters(
        movies: list[MovieRecommendation],
        hard_filters: HardFilters | None,
    ) -> list[MovieRecommendation]:
        if hard_filters is None:
            return movies
        filtered = [movie for movie in movies if RecommendationService._passes_hard_filters(movie, hard_filters)]
        return filtered or movies

    @staticmethod
    def _passes_hard_filters(movie: MovieRecommendation, hard_filters: HardFilters) -> bool:
        genre_names = {genre.lower() for genre in movie.genres}
        title_blob = " ".join(
            filter(
                None,
                [
                    movie.original_title.lower(),
                    (movie.overview or "").lower(),
                    " ".join(movie.genres).lower(),
                ],
            )
        )
        if hard_filters.include_genres and not any(genre.lower() in genre_names for genre in hard_filters.include_genres):
            return False
        if hard_filters.exclude_genres and any(genre.lower() in genre_names for genre in hard_filters.exclude_genres):
            return False
        if hard_filters.year_from is not None and (movie.year is None or movie.year < hard_filters.year_from):
            return False
        if hard_filters.year_to is not None and (movie.year is None or movie.year > hard_filters.year_to):
            return False
        if hard_filters.countries:
            countries = {country.lower() for country in movie.origin_countries}
            if not any(country.lower() in countries for country in hard_filters.countries):
                return False
        if hard_filters.min_runtime is not None and (movie.runtime_minutes is None or movie.runtime_minutes < hard_filters.min_runtime):
            return False
        if hard_filters.max_runtime is not None and (movie.runtime_minutes is None or movie.runtime_minutes > hard_filters.max_runtime):
            return False
        if hard_filters.min_rating is not None and (movie.vote_average is None or movie.vote_average < hard_filters.min_rating):
            return False
        if hard_filters.exclude_keywords and any(keyword.lower() in title_blob for keyword in hard_filters.exclude_keywords):
            return False
        return True


recommendation_service = RecommendationService()
