import hashlib
import hmac
import json
from dataclasses import dataclass
from time import time
from urllib.parse import parse_qsl

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import User
from app.schemas.auth import AuthenticatedTelegramUser, TelegramAuthPayload


@dataclass
class TelegramAuthService:
    def authenticate(self, payload: TelegramAuthPayload, db: Session) -> User:
        user_context = self._validate_init_data(payload.init_data_raw) if payload.init_data_raw else self._development_fallback(payload)

        user = db.get(User, user_context.telegram_id)
        if user is None:
            user = User(
                telegram_id=user_context.telegram_id,
                first_name=user_context.first_name,
                username=user_context.username,
            )
            db.add(user)
        else:
            user.first_name = user_context.first_name
            user.username = user_context.username

        db.flush()
        return user

    def _validate_init_data(self, init_data_raw: str) -> AuthenticatedTelegramUser:
        if not settings.telegram_bot_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="TELEGRAM_BOT_TOKEN is not configured",
            )

        parsed_items = dict(parse_qsl(init_data_raw, strict_parsing=True))
        received_hash = parsed_items.pop("hash", None)
        if not received_hash:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram hash is missing")

        auth_date_raw = parsed_items.get("auth_date")
        try:
            auth_date = int(auth_date_raw) if auth_date_raw is not None else 0
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram auth_date is invalid") from exc

        if settings.telegram_auth_max_age_seconds > 0:
            now = int(time())
            if auth_date <= 0 or now - auth_date > settings.telegram_auth_max_age_seconds:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram init data is expired")

        data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(parsed_items.items()))
        secret_key = hmac.new(b"WebAppData", settings.telegram_bot_token.encode("utf-8"), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram init data signature is invalid")

        user_raw = parsed_items.get("user")
        if not user_raw:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram user payload is missing")

        try:
            user_payload = json.loads(user_raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram user payload is invalid") from exc

        return AuthenticatedTelegramUser(
            telegram_id=int(user_payload["id"]),
            first_name=str(user_payload["first_name"]),
            username=user_payload.get("username"),
        )

    @staticmethod
    def _development_fallback(payload: TelegramAuthPayload) -> AuthenticatedTelegramUser:
        if settings.app_env != "development":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram init data is required")

        if payload.telegram_id is None or not payload.first_name:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Development auth payload is incomplete")

        return AuthenticatedTelegramUser(
            telegram_id=payload.telegram_id,
            first_name=payload.first_name,
            username=payload.username,
        )


telegram_auth_service = TelegramAuthService()
