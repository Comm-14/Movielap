from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import MovieFeedback
from app.db.session import get_db
from app.schemas.feedback import MovieFeedbackCreateRequest, MovieFeedbackResponse
from app.services.telegram_auth_service import telegram_auth_service

router = APIRouter()


@router.post("", response_model=MovieFeedbackResponse, status_code=status.HTTP_201_CREATED)
async def save_feedback(payload: MovieFeedbackCreateRequest, db: Session = Depends(get_db)) -> MovieFeedbackResponse:
    if payload.status not in {"seen", "skip_forever"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported feedback status")

    user = telegram_auth_service.authenticate(payload, db)
    existing = db.scalar(
        select(MovieFeedback).where(
            MovieFeedback.user_id == user.telegram_id,
            MovieFeedback.tmdb_id == payload.tmdb_id,
        )
    )
    if existing is None:
        existing = MovieFeedback(user_id=user.telegram_id, tmdb_id=payload.tmdb_id, status=payload.status)
        db.add(existing)
    else:
        existing.status = payload.status
        db.add(existing)

    db.commit()
    db.refresh(existing)
    return MovieFeedbackResponse.model_validate(existing, from_attributes=True)
