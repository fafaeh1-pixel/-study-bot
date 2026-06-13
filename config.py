from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str = "sqlite+aiosqlite:///studybot.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "studybot-secret-key-change-in-production"
    GEMINI_API_KEY: str = ""
    DASHBOARD_PASSWORD: str = "admin1234"

    # ── پریمیوم / زرین‌پال ──────────────────────────────────────
    ZARINPAL_MERCHANT_ID: str = ""
    WEBAPP_URL: str = "http://localhost:8000"
    BOT_USERNAME: str = ""
    PAYMENT_CALLBACK_URL: str = "https://yourdomain.com/payment/callback"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()