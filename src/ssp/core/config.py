import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GROQ_API_KEY: Optional[str] = None
    REDDIT_USER_AGENT: str = "windows:ssp-hunter:v1.0 (by /u/unknown)"
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    DATABASE_URL: str = "sqlite:///ssp.db"
    LOG_LEVEL: str = "INFO"
    
    FULL_CONTENT_MIN_SCORE: int = 60
    PARTIAL_CONTENT_MIN_SCORE: int = 45
    SNIPPET_CONTENT_MIN_SCORE: int = 35

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
