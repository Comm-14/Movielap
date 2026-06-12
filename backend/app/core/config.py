from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    app_name: str = "Movie Match API"
    app_env: str = "development"
    api_v1_prefix: str = "/api"
    database_url: str
    telegram_bot_username: str
    telegram_bot_token: str | None = None
    telegram_auth_max_age_seconds: int = 86400
    gemini_api_key: str
    gemini_model: str = "gemini-3.1-flash-lite"
    gemini_api_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    tmdb_api_key: str
    tmdb_api_base_url: str = "https://api.themoviedb.org/3"
    tmdb_image_base_url: str = "https://image.tmdb.org/t/p/w500"


settings = Settings()
