from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Session as SessionModel, Swipe
from app.db.session import get_db
from app.schemas.movie import MovieRecommendation
from app.schemas.swipe import SwipeCreateRequest, SwipeResponse
from app.services.auth_service import auth_service
from app.services.session_service import session_service
from app.websockets.manager import connection_manager

router = APIRouter()


@router.post("", response_model=SwipeResponse)
async def create_swipe(
    payload: SwipeCreateRequest,
    db: Session = Depends(get_db),
    authorization: str | None = Depends(auth_service.read_bearer_token),
) -> SwipeResponse:
    session = db.get(SessionModel, payload.session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.guest_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is waiting for the second user")

    user = auth_service.authenticate(
        db,
        authorization=authorization,
        init_data_raw=payload.init_data_raw,
        telegram_id=payload.telegram_id,
        first_name=payload.first_name,
        username=payload.username,
    )
    if user.id not in {session.creator_id, session.guest_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not part of this session")

    swipe = Swipe(
        session_id=payload.session_id,
        user_id=user.id,
        tmdb_id=payload.tmdb_id,
        action=payload.action,
    )
    db.add(swipe)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Movie already swiped in this session") from exc

    if payload.action != "like":
        return SwipeResponse(matched=False, movie=None)

    participant_ids = list(session.participant_ids or [session.creator_id] + ([session.guest_id] if session.guest_id else []))
    likes_count = db.scalar(
        select(func.count(Swipe.id)).where(
            Swipe.session_id == payload.session_id,
            Swipe.tmdb_id == payload.tmdb_id,
            Swipe.action == "like",
        )
    )
    if likes_count is None or likes_count < len(participant_ids):
        return SwipeResponse(matched=False, movie=None)

    session_movies = session_service.serialize_movies(session.movies_payload)
    movie = next((session_movie for session_movie in session_movies or [] if session_movie.tmdb_id == payload.tmdb_id), None)
    if movie is None:
        movie = MovieRecommendation(
            tmdb_id=payload.tmdb_id,
            original_title="Matched Movie",
            year=None,
            poster_path=None,
            vote_average=None,
            overview=None,
            genre_ids=[],
            reason_ru="Оба пользователя лайкнули этот фильм.",
            genres=[],
            runtime_minutes=None,
            origin_countries=[],
            match_summary_ru="Фильм совпал по лайкам у всех участников.",
            match_explainer=[],
            trailer_url=None,
            streaming_providers=[],
        )
    await connection_manager.broadcast(
        payload.session_id,
        {"event": "match_found", "session_id": str(payload.session_id), "movie": movie.model_dump()},
    )
    return SwipeResponse(matched=True, movie=movie)
