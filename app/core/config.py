from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Registrator ofisi murojaatlar va navbat axborot tizimi"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = "roffice_super_secret_jwt_key_2026_univer_jizzax_73"
    ALGORITHM: str = "HS256"
    STUDENT_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 2  # 2 days (48 hours)
    STAFF_TOKEN_EXPIRE_MINUTES: int = 60 * 12        # 12 hours

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./roffice.db"

    # Business Hours (Dushanba - Shanba: 09:00 - 17:00, Yakshanba dam olish)
    WORK_START_HOUR: int = 9
    WORK_END_HOUR: int = 17
    LUNCH_START_HOUR: int = 13
    LUNCH_END_HOUR: int = 14
    WORK_DAYS: List[int] = [0, 1, 2, 3, 4, 5]  # 0=Dushanba, 5=Shanba

    # HEMIS Integratsiya sozlamalari
    HEMIS_BASE_URL: str = "https://student.jbnuu.uz/rest/v1"
    HEMIS_TIMEOUT_SECONDS: int = 10

    # SLA & KPI Defaults
    ROUTING_WARNING_HOURS: int = 12
    ROUTING_MAX_HOURS: int = 24
    CONFIRMATION_TIMEOUT_HOURS: int = 72
    OVERDUE_PENALTY_POINTS: int = 5
    DEFAULT_MONTHLY_KPI_TARGET: int = 150

    # Telegram Bot Sozlamalari
    TELEGRAM_BOT_TOKEN: str = "YOUR_BOT_TOKEN_HERE"
    TELEGRAM_BOT_USERNAME: str = "roffice_jizzax_bot"

    # JBNUU HEMIS telefon raqamini tekshirish (Validate Phone) API
    JBNUU_VALIDATE_PHONE_URL: str = "https://student.jbnuu.uz/rest/v1/data/validate-phone"
    JBNUU_API_TOKEN: str = "Qn8Jp7TVvpGdQUvWoqpBC1i0p7ukHKT0"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
