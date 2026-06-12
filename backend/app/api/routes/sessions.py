from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import String, select
from sqlalchemy.orm import Session

from app.db.base import MovieFeedback, Session as SessionModel
from app.db.session import get_db
from app.schemas.session import SessionCreateRequest, SessionJoinRequest, SessionResponse
from app.services.auth_service import auth_service
from app.services.exceptions import ServiceIntegrationError
from app.services.recommendation_service import recommendation_service
from app.services.session_service import session_service
from app.websockets.manager import connection_manager

router = APIRouter()


@router.post("/create", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    authorization: str | None = Depends(auth_service.read_bearer_token),
) -> SessionResponse:
    user = auth_service.authenticate(
        db,
        authorization=authorization,
        init_data_raw=payload.init_data_raw,
        telegram_id=payload.telegram_id,
        first_name=payload.first_name,
        username=payload.username,
    )
    session_type = "duo" if payload.max_participants == 2 else "group"
    participant_profile = session_service.build_participant_profile(
        telegram_id=user.id,
        label="Тебе",
        preference_text=payload.preference_text,
        moods=payload.moods,
        hard_filters=payload.hard_filters.model_dump() if payload.hard_filters else None,
    )
    session = SessionModel(
        type=session_type,
        status="waiting",
        creator_id=user.id,
        preference_text_creator=payload.preference_text,
        participant_ids=[user.id],
        participant_profiles=[participant_profile],
        max_participants=payload.max_participants,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session_service.to_response(session, include_invite=True, request_base_url=str(request.base_url))


@router.get("/resolve/{invite_code}", response_model=SessionResponse)
async def resolve_session_by_invite_code(invite_code: str, request: Request, db: Session = Depends(get_db)) -> SessionResponse:
    normalized = invite_code.strip().lower()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    session = db.scalar(select(SessionModel).where(SessionModel.id.cast(String).like(f"{normalized}%")))
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session_service.to_response(session, include_invite=True, request_base_url=str(request.base_url))


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: UUID, request: Request, db: Session = Depends(get_db)) -> SessionResponse:
    session = db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session_service.to_response(session, include_invite=True, request_base_url=str(request.base_url))


@router.post("/join", response_model=SessionResponse)
async def join_session(
    payload: SessionJoinRequest,
    request: Request,
    db: Session = Depends(get_db),
    authorization: str | None = Depends(auth_service.read_bearer_token),
) -> SessionResponse:
    session = db.get(SessionModel, payload.session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    user = auth_service.authenticate(
        db,
        authorization=authorization,
        init_data_raw=payload.init_data_raw,
        telegram_id=payload.telegram_id,
        first_name=payload.first_name,
        username=payload.username,
    )
    participant_ids = list(session.participant_ids or [session.creator_id] + ([session.guest_id] if session.guest_id else []))
    if user.id in participant_ids:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already joined this session")
    if len(participant_ids) >= session.max_participants:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is already full")

    participant_ids.append(user.id)
    participant_profiles = list(session.participant_profiles or [])
    participant_profiles.append(
        session_service.build_participant_profile(
            telegram_id=user.id,
            label="Партнер" if len(participant_ids) == 2 else f"Участник {len(participant_ids)}",
            preference_text=payload.preference_text,
            moods=payload.moods,
            hard_filters=payload.hard_filters.model_dump() if payload.hard_filters else None,
        )
    )

    if len(participant_ids) == 2:
        session.guest_id = user.id
        session.preference_text_guest = payload.preference_text

    session.participant_ids = participant_ids
    session.participant_profiles = participant_profiles
    session.status = "active" if len(participant_ids) >= session.max_participants else "waiting"
    db.add(session)

    if session.status != "active":
        db.commit()
        db.refresh(session)
        return session_service.to_response(session, request_base_url=str(request.base_url))

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
    return session_service.to_response(session, request_base_url=str(request.base_url))
