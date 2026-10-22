from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    secret_key: str = "dev-secret-change-in-production"
    database_url: str = "sqlite:///./data/app.db"
    environment: str = "development"
    default_timezone: str = "America/New_York"
    default_currency: str = "USD"
    access_token_expire_minutes: int = 480

    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_ai_api_key: Optional[str] = None
    xai_api_key: Optional[str] = None

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
