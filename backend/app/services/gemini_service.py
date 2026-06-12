import json
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.filters import HardFilters
from app.schemas.movie import GeminiMovieCandidate, GeminiRecommendationPayload
from app.services.exceptions import ServiceIntegrationError

GEMINI_SYSTEM_PROMPT = (
    "You are a movie expert. Generate exactly 10 movie recommendations based on user preferences. "
    "For shared sessions, find compromises that satisfy everyone. Return STRICTLY a valid JSON object. "
    "Each item must contain original_title, year, reason_ru, optional match_summary_ru, and optional match_explainer. "
    "match_explainer should explain why the movie fits each participant. "
    "reason_ru must be in Russian and no longer than 150 characters."
)


class GeminiService:
    async def recommend_movies(
        self,
        preference_text: str,
        *,
        participant_labels: list[str] | None = None,
        moods: list[str] | None = None,
        hard_filters: HardFilters | None = None,
    ) -> list[GeminiMovieCandidate]:
        moods_text = ", ".join(moods or []) or "нет"
        participant_text = ", ".join(participant_labels or ["Пользователь"])
        filters_text = self._format_hard_filters(hard_filters)
        payload = {
            "system_instruction": {"parts": [{"text": GEMINI_SYSTEM_PROMPT}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                "Session participants:\n"
                                f"{participant_text}\n\n"
                                "Mood presets:\n"
                                f"{moods_text}\n\n"
                                "Hard filters:\n"
                                f"{filters_text}\n\n"
                                "User preferences:\n"
                                f"{preference_text}\n\n"
                                "Return only JSON with this shape: "
                                '{"movies":[{"original_title":"Fight Club","year":1999,"reason_ru":"...",'
                                '"match_summary_ru":"...",'
                                '"match_explainer":[{"audience_label":"Тебе","reason_ru":"..."}]}]}'
                            )
                        }
                    ],
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "required": ["movies"],
                    "properties": {
                        "movies": {
                            "type": "ARRAY",
                            "minItems": 10,
                            "maxItems": 10,
                            "items": {
                                "type": "OBJECT",
                                "required": ["original_title", "year", "reason_ru"],
                                "properties": {
                                    "original_title": {"type": "STRING"},
                                    "year": {"type": "INTEGER"},
                                    "reason_ru": {"type": "STRING"},
                                    "match_summary_ru": {"type": "STRING"},
                                    "match_explainer": {
                                        "type": "ARRAY",
                                        "items": {
                                            "type": "OBJECT",
                                            "required": ["audience_label", "reason_ru"],
                                            "properties": {
                                                "audience_label": {"type": "STRING"},
                                                "reason_ru": {"type": "STRING"},
                                            },
                                        },
                                    },
                                },
                            },
                        }
                    },
                },
                "temperature": 0.7,
            },
        }

        url = f"{settings.gemini_api_base_url}/models/{settings.gemini_model}:generateContent"
        params = {"key": settings.gemini_api_key}

        async with httpx.AsyncClient(timeout=httpx.Timeout(25.0)) as client:
            try:
                response = await client.post(url, params=params, json=payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = self._extract_error_detail(exc.response)
                raise ServiceIntegrationError(f"Gemini API error: {detail}") from exc
            except httpx.HTTPError as exc:
                raise ServiceIntegrationError(f"Gemini API request failed: {exc}") from exc

        raw_text = self._extract_response_text(response.json())
        if not raw_text:
            raise ServiceIntegrationError("Gemini API returned an empty response")

        try:
            parsed_payload = GeminiRecommendationPayload.model_validate(json.loads(self._strip_code_fences(raw_text)))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ServiceIntegrationError("Gemini response is not valid recommendation JSON") from exc

        candidates = parsed_payload.movies[:10]
        if not candidates:
            raise ServiceIntegrationError("Gemini returned no movie recommendations")
        return candidates

    @staticmethod
    def _extract_response_text(payload: dict[str, Any]) -> str:
        candidates = payload.get("candidates", [])
        for candidate in candidates:
            content = candidate.get("content", {})
            for part in content.get("parts", []):
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    return text
        return ""

    @staticmethod
    def _extract_error_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text or f"HTTP {response.status_code}"

        error = payload.get("error", {})
        message = error.get("message")
        if isinstance(message, str) and message:
            return message
        return response.text or f"HTTP {response.status_code}"

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = stripped.removeprefix("```json").removeprefix("```JSON").removeprefix("```").strip()
            if stripped.endswith("```"):
                stripped = stripped[:-3].strip()
        return stripped

    @staticmethod
    def _format_hard_filters(filters: HardFilters | None) -> str:
        if filters is None:
            return "нет"
        parts: list[str] = []
        if filters.include_genres:
            parts.append(f"включить жанры: {', '.join(filters.include_genres)}")
        if filters.exclude_genres:
            parts.append(f"исключить жанры: {', '.join(filters.exclude_genres)}")
        if filters.year_from is not None or filters.year_to is not None:
            parts.append(f"годы: {filters.year_from or 'any'}-{filters.year_to or 'any'}")
        if filters.countries:
            parts.append(f"страны: {', '.join(filters.countries)}")
        if filters.min_runtime is not None or filters.max_runtime is not None:
            parts.append(f"длительность: {filters.min_runtime or 0}-{filters.max_runtime or 'any'} мин")
        if filters.min_rating is not None:
            parts.append(f"минимальный рейтинг: {filters.min_rating}")
        if filters.exclude_keywords:
            parts.append(f"исключить темы: {', '.join(filters.exclude_keywords)}")
        return "; ".join(parts) or "нет"


gemini_service = GeminiService()
