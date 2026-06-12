import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import MovieFeedback
from app.db.session import get_db
from app.schemas.recommendation import RecommendationResponse, SoloRecommendationRequest
from app.services.exceptions import ServiceIntegrationError
from app.services.recommendation_service import recommendation_service
from app.services.telegram_auth_service import telegram_auth_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/solo", response_model=RecommendationResponse)
async def solo_recommendations(payload: SoloRecommendationRequest, db: Session = Depends(get_db)) -> RecommendationResponse:
    user = telegram_auth_service.authenticate(payload, db)
    db.commit()
    try:
        movies = await recommendation_service.build_solo_recommendations(
            payload.preference_text,
            moods=payload.moods,
            hard_filters=payload.hard_filters,
        )
    except ServiceIntegrationError as exc:
        logger.exception("Recommendation pipeline failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    excluded_tmdb_ids = set(
        db.scalars(
            select(MovieFeedback.tmdb_id).where(
                MovieFeedback.user_id == user.telegram_id,
                MovieFeedback.status.in_(["seen", "skip_forever"]),
            )
        ).all()
    )
    movies = [movie for movie in movies if movie.tmdb_id not in excluded_tmdb_ids]
    return RecommendationResponse(movies=movies)
