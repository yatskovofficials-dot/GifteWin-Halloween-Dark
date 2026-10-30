from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    BOT_TOKEN: str
    ADMIN_IDS: str = ""
    CHANNEL_USERNAME: str = "GifteWin"
    CHANNEL_LINK: str = "https://t.me/GifteWin"
    BOT_USERNAME: str = "GifteWinBot"
    DATABASE_PATH: str = "data/giftewin.db"
    TIMEZONE: str = "Europe/Kyiv"
    REFERRAL_BONUS_BALLS: int = 10
    MAX_BALLS_PER_USER: int = 500
    MIN_PARTICIPANTS: int = 2

    @property
    def admin_ids(self) -> List[int]:
        if not self.ADMIN_IDS.strip():
            return []
        return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip()]

    @property
    def db_path(self) -> Path:
        return Path(self.DATABASE_PATH)


settings = Settings()
