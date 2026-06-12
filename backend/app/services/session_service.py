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
    def build_invite_link(session_id: UUID) -> str:
        return f"https://t.me/{settings.telegram_bot_username}/app?startapp=session_{session_id}"

    def to_response(self, session: SessionModel, include_invite: bool = False) -> SessionResponse:
        participant_ids = list(session.participant_ids or [session.creator_id] + ([session.guest_id] if session.guest_id else []))
        return SessionResponse(
            id=session.id,
            type=session.type,
            status=session.status,
            creator_id=session.creator_id,
            guest_id=session.guest_id,
            participant_ids=participant_ids,
            max_participants=session.max_participants,
            invite_link=self.build_invite_link(session.id) if include_invite else None,
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
            "telegram_id": telegram_id,
            "label": label,
            "preference_text": preference_text,
            "moods": moods,
            "hard_filters": hard_filters,
        }


session_service = SessionService()
