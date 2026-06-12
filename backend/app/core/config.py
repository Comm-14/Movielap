from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    app_name: str = "Movie Match API"
    app_env: str = "development"
    api_v1_prefix: str = "/api"
    database_url: str
    telegram_bot_username: str
    web_app_base_url: str = "http://localhost:5173"
    telegram_bot_token: str | None = None
    telegram_auth_max_age_seconds: int = 86400
    auth_token_secret: str = "change-me"
    auth_cookie_name: str = "movielap_auth"
    auth_cookie_secure: bool = True
    cors_allowed_origins: str = ""
    gemini_api_key: str
    gemini_model: str = "gemini-3.1-flash-lite"
    gemini_api_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    tmdb_api_key: str
    tmdb_api_base_url: str = "https://api.themoviedb.org/3"
    tmdb_image_base_url: str = "https://image.tmdb.org/t/p/w500"

    @property
    def resolved_cors_origins(self) -> list[str]:
        configured = [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]
        if configured:
            return configured
        if self.app_env == "development":
            return [
                "http://localhost:3000",
                "http://localhost:4173",
                "http://localhost:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:4173",
                "http://127.0.0.1:5173",
            ]
        return []


settings = Settings()
