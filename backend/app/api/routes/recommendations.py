import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import MovieFeedback
from app.db.session import get_db
from app.schemas.recommendation import RecommendationResponse, SoloRecommendationRequest
from app.services.auth_service import auth_service
from app.services.exceptions import ServiceIntegrationError
from app.services.recommendation_service import recommendation_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/solo", response_model=RecommendationResponse)
async def solo_recommendations(
    payload: SoloRecommendationRequest,
    db: Session = Depends(get_db),
    authorization: str | None = Depends(auth_service.read_bearer_token),
    auth_cookie: str | None = Depends(auth_service.read_auth_cookie),
) -> RecommendationResponse:
    user = auth_service.authenticate(
        db,
        authorization=authorization,
        auth_cookie=auth_cookie,
        init_data_raw=payload.init_data_raw,
        telegram_id=payload.telegram_id,
        first_name=payload.first_name,
        username=payload.username,
    )
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
                MovieFeedback.user_id == user.id,
                MovieFeedback.status.in_(["seen", "skip_forever"]),
            )
        ).all()
    )
    movies = [movie for movie in movies if movie.tmdb_id not in excluded_tmdb_ids]
    return RecommendationResponse(movies=movies)
