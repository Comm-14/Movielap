from uuid import UUID

from app.core.config import settings
from app.db.base import Session as SessionModel
from app.schemas.movie import MovieRecommendation
from app.schemas.session import SessionResponse


class SessionService:
    @staticmethod
    def serialize_movies(movies_payload: list[dict] | None) -> list[MovieRecommendation] | None:
        if not movies_payload:
            return None
        return [MovieRecommendation.model_validate(movie_payload) for movie_payload in movies_payload]

    @staticmethod
    def build_invite_link(session_id: UUID, request_base_url: str | None = None) -> str:
        base_url = settings.web_app_base_url.rstrip("/") if settings.web_app_base_url else ""
        if request_base_url:
            normalized_request_base_url = request_base_url.rstrip("/")
            if not base_url or "localhost:5173" in base_url:
                base_url = normalized_request_base_url
        return f"{base_url}/session/{session_id}"

    def to_response(
        self,
        session: SessionModel,
        include_invite: bool = False,
        request_base_url: str | None = None,
    ) -> SessionResponse:
        participant_ids = list(session.participant_ids or [session.creator_id] + ([session.guest_id] if session.guest_id else []))
        return SessionResponse(
            id=session.id,
            type=session.type,
            status=session.status,
            creator_id=session.creator_id,
            guest_id=session.guest_id,
            participant_ids=participant_ids,
            max_participants=session.max_participants,
            invite_link=self.build_invite_link(session.id, request_base_url) if include_invite else None,
            invite_code=str(session.id)[:8].upper(),
            created_at=session.created_at,
            movies=self.serialize_movies(session.movies_payload),
        )

    @staticmethod
    def build_participant_profile(
        *,
        telegram_id: int,
        label: str,
        preference_text: str,
        moods: list[str],
        hard_filters: dict | None,
    ) -> dict:
        return {
            "user_id": telegram_id,
            "label": label,
            "preference_text": preference_text,
            "moods": moods,
            "hard_filters": hard_filters,
        }


session_service = SessionService()
