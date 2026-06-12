from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings
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


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
        max_age=60 * 60 * 24 * 30,
    )


@router.post("/guest", response_model=AuthUserResponse)
async def sign_in_as_guest(payload: GuestAuthRequest, response: Response, db: Session = Depends(get_db)) -> AuthUserResponse:
    user, token = auth_service.create_guest_user(db, payload.name)
    db.commit()
    _set_auth_cookie(response, token)
    return _build_auth_response(user.id, user.first_name, user.username, "guest", token)


@router.post("/telegram", response_model=AuthUserResponse)
async def sign_in_with_telegram(payload: TelegramSignInRequest, response: Response, db: Session = Depends(get_db)) -> AuthUserResponse:
    user = auth_service.authenticate(db, init_data_raw=payload.init_data_raw)
    db.commit()
    token = auth_service.issue_token(user.id)
    _set_auth_cookie(response, token)
    return _build_auth_response(user.id, user.first_name, user.username, "telegram", token)


@router.get("/me", response_model=AuthUserResponse)
async def get_me(
    response: Response,
    db: Session = Depends(get_db),
    authorization: str | None = Depends(auth_service.read_bearer_token),
    auth_cookie: str | None = Depends(auth_service.read_auth_cookie),
) -> AuthUserResponse:
    user = auth_service.require_authenticated_user(db, authorization, auth_cookie)
    token = auth_service.issue_token(user.id)
    _set_auth_cookie(response, token)
    return _build_auth_response(user.id, user.first_name, user.username, "token", token)
