from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import MovieFeedback, Session as SessionModel
from app.db.session import get_db
from app.schemas.session import SessionCreateRequest, SessionJoinRequest, SessionResponse
from app.services.exceptions import ServiceIntegrationError
from app.services.recommendation_service import recommendation_service
from app.services.session_service import session_service
from app.services.telegram_auth_service import telegram_auth_service
from app.websockets.manager import connection_manager

router = APIRouter()


@router.post("/create", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(payload: SessionCreateRequest, db: Session = Depends(get_db)) -> SessionResponse:
    user = telegram_auth_service.authenticate(payload, db)
    session_type = "duo" if payload.max_participants == 2 else "group"
    participant_profile = session_service.build_participant_profile(
        telegram_id=user.telegram_id,
        label="Тебе",
        preference_text=payload.preference_text,
        moods=payload.moods,
        hard_filters=payload.hard_filters.model_dump() if payload.hard_filters else None,
    )
    session = SessionModel(
        type=session_type,
        status="waiting",
        creator_id=user.telegram_id,
        preference_text_creator=payload.preference_text,
        participant_ids=[user.telegram_id],
        participant_profiles=[participant_profile],
        max_participants=payload.max_participants,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session_service.to_response(session, include_invite=True)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: UUID, db: Session = Depends(get_db)) -> SessionResponse:
    session = db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session_service.to_response(session, include_invite=True)


@router.post("/join", response_model=SessionResponse)
async def join_session(payload: SessionJoinRequest, db: Session = Depends(get_db)) -> SessionResponse:
    session = db.get(SessionModel, payload.session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    user = telegram_auth_service.authenticate(payload, db)
    participant_ids = list(session.participant_ids or [session.creator_id] + ([session.guest_id] if session.guest_id else []))
    if user.telegram_id in participant_ids:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already joined this session")
    if len(participant_ids) >= session.max_participants:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is already full")

    participant_ids.append(user.telegram_id)
    participant_profiles = list(session.participant_profiles or [])
    participant_profiles.append(
        session_service.build_participant_profile(
            telegram_id=user.telegram_id,
            label="Партнер" if len(participant_ids) == 2 else f"Участник {len(participant_ids)}",
            preference_text=payload.preference_text,
            moods=payload.moods,
            hard_filters=payload.hard_filters.model_dump() if payload.hard_filters else None,
        )
    )

    if len(participant_ids) == 2:
        session.guest_id = user.telegram_id
        session.preference_text_guest = payload.preference_text

    session.participant_ids = participant_ids
    session.participant_profiles = participant_profiles
    session.status = "active" if len(participant_ids) >= session.max_participants else "waiting"
    db.add(session)

    if session.status != "active":
        db.commit()
        db.refresh(session)
        return session_service.to_response(session)

    try:
        movies = await recommendation_service.build_group_recommendations(participant_profiles)
    except ServiceIntegrationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    excluded_tmdb_ids = set(
        db.scalars(
            select(MovieFeedback.tmdb_id).where(
                MovieFeedback.user_id.in_(participant_ids),
                MovieFeedback.status.in_(["seen", "skip_forever"]),
            )
        ).all()
    )
    movies = [movie for movie in movies if movie.tmdb_id not in excluded_tmdb_ids]
    session.movies_payload = [movie.model_dump() for movie in movies]
    db.add(session)
    db.commit()
    db.refresh(session)

    await connection_manager.broadcast(
        session.id,
        {"event": "movies_ready", "session_id": str(session.id), "movies": session.movies_payload},
    )
    return session_service.to_response(session)
