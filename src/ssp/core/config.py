import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GROQ_API_KEY: str = ""
    REDDIT_USER_AGENT: str = "ssp_hunter:v1.0 (by /u/YOUR_USERNAME)"
    DATABASE_URL: str = "sqlite:///data/ssp.db"
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
