from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Watchlist
from app.db.session import get_db
from app.schemas.watchlist import WatchlistAddRequest, WatchlistItemResponse
from app.services.exceptions import ServiceIntegrationError
from app.services.telegram_auth_service import telegram_auth_service
from app.services.tmdb_service import tmdb_service

router = APIRouter()


def _normalize_watchlist_item(item: Watchlist) -> Watchlist:
    item.genre_ids = item.genre_ids or []
    item.genres = item.genres or []
    item.origin_countries = item.origin_countries or []
    return item


@router.post("/add", response_model=WatchlistItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(payload: WatchlistAddRequest, db: Session = Depends(get_db)) -> WatchlistItemResponse:
    user = telegram_auth_service.authenticate(payload, db)
    movie = payload.movie
    item = Watchlist(
        user_id=user.telegram_id,
        tmdb_id=payload.tmdb_id,
        original_title=movie.original_title if movie else None,
        year=movie.year if movie else None,
        poster_path=movie.poster_path if movie else None,
        vote_average=movie.vote_average if movie else None,
        overview=movie.overview if movie else None,
        genre_ids=movie.genre_ids if movie else None,
        genres=movie.genres if movie else None,
        runtime_minutes=movie.runtime_minutes if movie else None,
        origin_countries=movie.origin_countries if movie else None,
        reason_ru=movie.reason_ru if movie else None,
        match_summary_ru=movie.match_summary_ru if movie else None,
    )
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Movie already in watchlist") from exc
    db.refresh(item)
    _normalize_watchlist_item(item)
    return WatchlistItemResponse.model_validate(item, from_attributes=True)


@router.get("/{user_id}", response_model=list[WatchlistItemResponse])
async def get_watchlist(user_id: int, db: Session = Depends(get_db)) -> list[WatchlistItemResponse]:
    items = db.scalars(select(Watchlist).where(Watchlist.user_id == user_id).order_by(Watchlist.added_at.desc())).all()
    responses: list[WatchlistItemResponse] = []

    for item in items:
        if not item.original_title:
            try:
                movie = await tmdb_service.get_movie_details(item.tmdb_id, reason_ru=item.reason_ru)
            except ServiceIntegrationError:
                movie = None

            if movie is not None:
                item.original_title = movie.original_title
                item.year = movie.year
                item.poster_path = movie.poster_path
                item.vote_average = movie.vote_average
                item.overview = movie.overview
                item.genre_ids = movie.genre_ids
                item.genres = movie.genres
                item.runtime_minutes = movie.runtime_minutes
                item.origin_countries = movie.origin_countries
                item.reason_ru = item.reason_ru or movie.reason_ru
                item.match_summary_ru = item.match_summary_ru or movie.match_summary_ru
                db.add(item)

        _normalize_watchlist_item(item)
        responses.append(WatchlistItemResponse.model_validate(item, from_attributes=True))

    if db.dirty:
        db.commit()
    return responses
