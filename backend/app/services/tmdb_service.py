import asyncio
from typing import Any

import httpx

from app.core.config import settings
from app.schemas.movie import GeminiMovieCandidate, MovieRecommendation
from app.services.exceptions import ServiceIntegrationError


class TmdbService:
    async def enrich_movies(self, candidates: list[GeminiMovieCandidate]) -> list[MovieRecommendation]:
        if not candidates:
            return []

        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0)) as client:
            semaphore = asyncio.Semaphore(5)
            tasks = [self._search_movie(client, semaphore, candidate) for candidate in candidates]
            results = await asyncio.gather(*tasks)

        movies = [movie for movie in results if movie is not None]
        if not movies:
            raise ServiceIntegrationError("TMDB returned no usable movie matches")
        return movies

    async def _search_movie(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        candidate: GeminiMovieCandidate,
    ) -> MovieRecommendation | None:
        params = {
            "api_key": settings.tmdb_api_key,
            "query": candidate.original_title,
            "language": "ru-RU",
            "include_adult": "false",
        }
        if candidate.year is not None:
            params["year"] = str(candidate.year)

        url = f"{settings.tmdb_api_base_url}/search/movie"

        async with semaphore:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = self._extract_error_detail(exc.response)
                raise ServiceIntegrationError(f"TMDB API error: {detail}") from exc
            except httpx.HTTPError as exc:
                raise ServiceIntegrationError(f"TMDB API request failed: {exc}") from exc

        payload = response.json()
        results = payload.get("results", [])
        if not results:
            return None

        best_match = self._pick_best_match(candidate, results)
        if best_match is None:
            return None

        details = await self._fetch_movie_details_bundle(client, semaphore, int(best_match["id"]))
        return MovieRecommendation(
            tmdb_id=int(best_match["id"]),
            original_title=str(best_match.get("original_title") or best_match.get("title") or candidate.original_title),
            year=self._extract_year(best_match.get("release_date")) or details.get("year") or candidate.year,
            poster_path=best_match.get("poster_path"),
            vote_average=float(best_match["vote_average"]) if best_match.get("vote_average") is not None else None,
            overview=best_match.get("overview") or details.get("overview"),
            genre_ids=[int(item) for item in best_match.get("genre_ids", []) if isinstance(item, int)],
            genres=details.get("genres", []),
            runtime_minutes=details.get("runtime_minutes"),
            origin_countries=details.get("origin_countries", []),
            reason_ru=candidate.reason_ru,
            match_summary_ru=candidate.match_summary_ru or candidate.reason_ru,
            match_explainer=candidate.match_explainer,
            trailer_url=details.get("trailer_url"),
            streaming_providers=details.get("streaming_providers", []),
        )

    async def get_movie_details(self, tmdb_id: int, reason_ru: str | None = None) -> MovieRecommendation | None:
        params = {
            "api_key": settings.tmdb_api_key,
            "language": "ru-RU",
        }
        url = f"{settings.tmdb_api_base_url}/movie/{tmdb_id}"

        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0)) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = self._extract_error_detail(exc.response)
                raise ServiceIntegrationError(f"TMDB API error: {detail}") from exc
            except httpx.HTTPError as exc:
                raise ServiceIntegrationError(f"TMDB API request failed: {exc}") from exc

        payload = response.json()
        details = await self._fetch_movie_details_bundle(client, asyncio.Semaphore(1), tmdb_id)
        return MovieRecommendation(
            tmdb_id=int(payload["id"]),
            original_title=str(payload.get("original_title") or payload.get("title") or tmdb_id),
            year=self._extract_year(payload.get("release_date")),
            poster_path=payload.get("poster_path"),
            vote_average=float(payload["vote_average"]) if payload.get("vote_average") is not None else None,
            overview=payload.get("overview"),
            genre_ids=[int(item["id"]) for item in payload.get("genres", []) if isinstance(item, dict) and item.get("id") is not None],
            genres=details.get("genres", []),
            runtime_minutes=details.get("runtime_minutes"),
            origin_countries=details.get("origin_countries", []),
            reason_ru=reason_ru or "Сохранено в watchlist.",
            match_summary_ru=reason_ru or "Сохранено в watchlist.",
            trailer_url=details.get("trailer_url"),
            streaming_providers=details.get("streaming_providers", []),
        )

    async def _fetch_movie_details_bundle(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        tmdb_id: int,
    ) -> dict[str, Any]:
        details_url = f"{settings.tmdb_api_base_url}/movie/{tmdb_id}"
        videos_url = f"{settings.tmdb_api_base_url}/movie/{tmdb_id}/videos"
        providers_url = f"{settings.tmdb_api_base_url}/movie/{tmdb_id}/watch/providers"
        params = {"api_key": settings.tmdb_api_key, "language": "ru-RU"}

        async with semaphore:
            try:
                details_response, videos_response, providers_response = await asyncio.gather(
                    client.get(details_url, params=params),
                    client.get(videos_url, params=params),
                    client.get(providers_url, params={"api_key": settings.tmdb_api_key}),
                )
                details_response.raise_for_status()
                videos_response.raise_for_status()
                providers_response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = self._extract_error_detail(exc.response)
                raise ServiceIntegrationError(f"TMDB API error: {detail}") from exc
            except httpx.HTTPError as exc:
                raise ServiceIntegrationError(f"TMDB API request failed: {exc}") from exc

        details_payload = details_response.json()
        videos_payload = videos_response.json()
        providers_payload = providers_response.json()
        return {
            "year": self._extract_year(details_payload.get("release_date")),
            "overview": details_payload.get("overview"),
            "genres": [
                str(item.get("name"))
                for item in details_payload.get("genres", [])
                if isinstance(item, dict) and item.get("name")
            ],
            "runtime_minutes": details_payload.get("runtime"),
            "origin_countries": [
                str(item.get("iso_3166_1"))
                for item in details_payload.get("production_countries", [])
                if isinstance(item, dict) and item.get("iso_3166_1")
            ],
            "trailer_url": self._extract_trailer_url(videos_payload),
            "streaming_providers": self._extract_streaming_providers(providers_payload),
        }

    @staticmethod
    def _pick_best_match(candidate: GeminiMovieCandidate, results: list[dict[str, Any]]) -> dict[str, Any] | None:
        normalized_query = TmdbService._normalize_title(candidate.original_title)
        target_year = candidate.year
        scored_results: list[tuple[int, dict[str, Any]]] = []

        for result in results:
            title = str(result.get("original_title") or result.get("title") or "")
            normalized_title = TmdbService._normalize_title(title)
            year = TmdbService._extract_year(result.get("release_date"))

            score = 0
            if normalized_title == normalized_query:
                score += 100
            elif normalized_query in normalized_title or normalized_title in normalized_query:
                score += 50

            if target_year is not None and year == target_year:
                score += 40
            elif target_year is not None and year is not None:
                score += max(0, 15 - abs(year - target_year))

            vote_average = result.get("vote_average")
            if isinstance(vote_average, (int, float)):
                score += int(vote_average)

            scored_results.append((score, result))

        if not scored_results:
            return None

        scored_results.sort(key=lambda item: item[0], reverse=True)
        best_score, best_result = scored_results[0]
        return best_result if best_score > 0 else None

    @staticmethod
    def _normalize_title(title: str) -> str:
        return "".join(character.lower() for character in title if character.isalnum())

    @staticmethod
    def _extract_year(release_date: Any) -> int | None:
        if not isinstance(release_date, str) or len(release_date) < 4:
            return None
        try:
            return int(release_date[:4])
        except ValueError:
            return None

    @staticmethod
    def _extract_error_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text or f"HTTP {response.status_code}"

        status_message = payload.get("status_message")
        if isinstance(status_message, str) and status_message:
            return status_message
        return response.text or f"HTTP {response.status_code}"

    @staticmethod
    def _extract_trailer_url(payload: dict[str, Any]) -> str | None:
        for item in payload.get("results", []):
            if not isinstance(item, dict):
                continue
            if item.get("site") == "YouTube" and item.get("type") == "Trailer" and item.get("key"):
                return f"https://www.youtube.com/watch?v={item['key']}"
        return None

    @staticmethod
    def _extract_streaming_providers(payload: dict[str, Any]) -> list[dict[str, str]]:
        results = payload.get("results", {})
        for region in ("RU", "US"):
            region_payload = results.get(region)
            if not isinstance(region_payload, dict):
                continue
            flatrate = region_payload.get("flatrate", [])
            providers = []
            for item in flatrate[:5]:
                if isinstance(item, dict) and item.get("provider_name"):
                    providers.append({"name": str(item["provider_name"])})
            if providers:
                return providers
        return []


tmdb_service = TmdbService()
