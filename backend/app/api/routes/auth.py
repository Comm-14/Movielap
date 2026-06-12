from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import AuthUserResponse, GuestAuthRequest, TelegramSignInRequest
from app.services.auth_service import auth_service

router = APIRouter()


def _build_auth_response(user_id: int, first_name: str, username: str | None, auth_provider: str, token: str) -> AuthUserResponse:
    return AuthUserResponse(
        user_id=user_id,
        first_name=first_name,
        username=username,
        auth_provider=auth_provider,
        token=token,
    )


@router.post("/guest", response_model=AuthUserResponse)
async def sign_in_as_guest(payload: GuestAuthRequest, db: Session = Depends(get_db)) -> AuthUserResponse:
    user, token = auth_service.create_guest_user(db, payload.name)
    db.commit()
    return _build_auth_response(user.id, user.first_name, user.username, "guest", token)


@router.post("/telegram", response_model=AuthUserResponse)
async def sign_in_with_telegram(payload: TelegramSignInRequest, db: Session = Depends(get_db)) -> AuthUserResponse:
    user = auth_service.authenticate(db, init_data_raw=payload.init_data_raw)
    db.commit()
    return _build_auth_response(user.id, user.first_name, user.username, "telegram", auth_service.issue_token(user.id))


@router.get("/me", response_model=AuthUserResponse)
async def get_me(
    db: Session = Depends(get_db),
    authorization: str | None = Depends(auth_service.read_bearer_token),
) -> AuthUserResponse:
    user = auth_service.require_authenticated_user(db, authorization)
    return _build_auth_response(user.id, user.first_name, user.username, "token", auth_service.issue_token(user.id))
