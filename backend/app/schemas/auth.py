from pydantic import BaseModel


class TelegramAuthPayload(BaseModel):
    init_data_raw: str | None = None
    telegram_id: int | None = None
    first_name: str | None = None
    username: str | None = None


class AuthenticatedTelegramUser(BaseModel):
    telegram_id: int
    first_name: str
    username: str | None = None


class GuestAuthRequest(BaseModel):
    name: str


class TelegramSignInRequest(BaseModel):
    init_data_raw: str


class AuthUserResponse(BaseModel):
    user_id: int
    first_name: str
    username: str | None = None
    auth_provider: str
    token: str
