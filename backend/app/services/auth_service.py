import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from time import time
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import User


@dataclass
class AuthUserContext:
    user_id: int
    first_name: str
    username: str | None
    provider: str


@dataclass
class AuthService:
    def authenticate(
        self,
        db: Session,
        *,
        authorization: str | None = None,
        init_data_raw: str | None = None,
        telegram_id: int | None = None,
        first_name: str | None = None,
        username: str | None = None,
    ) -> User:
        if authorization:
            user_id = self._authenticate_bearer_token(authorization)
            user = db.get(User, user_id)
            if user is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authenticated user was not found")
            return user
        elif init_data_raw:
            context = self._validate_telegram_init_data(init_data_raw)
        else:
            context = self._development_fallback(
                telegram_id=telegram_id,
                first_name=first_name,
                username=username,
            )

        user = db.get(User, context.user_id)
        if user is None:
            user = User(
                telegram_id=context.user_id,
                first_name=context.first_name,
                username=context.username,
            )
            db.add(user)
        else:
            user.first_name = context.first_name
            user.username = context.username

        db.flush()
        return user

    def require_authenticated_user(self, db: Session, authorization: str | None) -> User:
        if not authorization:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header is required")
        return self.authenticate(db, authorization=authorization)

    def create_guest_user(self, db: Session, name: str) -> tuple[User, str]:
        display_name = name.strip()
        if len(display_name) < 2:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Guest name must be at least 2 characters")

        user_id = self._generate_guest_user_id(db)
        user = User(telegram_id=user_id, first_name=display_name, username=None)
        db.add(user)
        db.flush()
        return user, self.issue_token(user.id)

    def issue_token(self, user_id: int) -> str:
        payload = {"user_id": user_id, "issued_at": int(time())}
        payload_raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(payload_raw).decode("utf-8").rstrip("=")
        signature = hmac.new(settings.auth_token_secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{payload_b64}.{signature}"

    def read_bearer_token(self, authorization: str = Header(default=None)) -> str | None:
        return authorization

    def _authenticate_bearer_token(self, authorization: str) -> int:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization scheme")

        try:
            payload_b64, signature = token.split(".", 1)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token") from exc

        expected_signature = hmac.new(
            settings.auth_token_secret.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected_signature, signature):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token signature")

        padded_payload = payload_b64 + "=" * (-len(payload_b64) % 4)
        try:
            payload = json.loads(base64.urlsafe_b64decode(padded_payload.encode("utf-8")).decode("utf-8"))
            user_id = int(payload["user_id"])
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token payload") from exc

        return user_id

    def _validate_telegram_init_data(self, init_data_raw: str) -> AuthUserContext:
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

        return AuthUserContext(
            user_id=int(user_payload["id"]),
            first_name=str(user_payload["first_name"]),
            username=user_payload.get("username"),
            provider="telegram",
        )

    @staticmethod
    def _development_fallback(*, telegram_id: int | None, first_name: str | None, username: str | None) -> AuthUserContext:
        if settings.app_env != "development":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required")

        if telegram_id is None or not first_name:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Development auth payload is incomplete")

        return AuthUserContext(
            user_id=telegram_id,
            first_name=first_name,
            username=username,
            provider="development",
        )

    @staticmethod
    def _generate_guest_user_id(db: Session) -> int:
        while True:
            candidate = -secrets.randbelow(10**12)
            exists = db.scalar(select(User.telegram_id).where(User.telegram_id == candidate))
            if exists is None:
                return candidate


auth_service = AuthService()
