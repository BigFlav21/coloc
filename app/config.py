from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET = "dev-insecure-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="COLOC_", extra="ignore")

    secret_key: str = DEFAULT_SECRET
    database_url: str = "sqlite:///./data/coloc.db"
    cookie_secure: bool = False
    session_days: int = 90
    timezone: str = "Europe/Paris"
