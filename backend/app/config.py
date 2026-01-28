from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path
from typing import Optional

# Get the backend directory (parent of app/)
BACKEND_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database - supports DATABASE_URL (Railway) or individual vars (legacy)
    database_url: Optional[str] = None

    # Legacy individual vars (fallback if DATABASE_URL not set)
    supabase_db_host: Optional[str] = None
    supabase_db_port: int = 5432
    supabase_db_name: str = "postgres"
    supabase_db_user: str = "postgres"
    supabase_db_password: Optional[str] = None

    # API
    api_title: str = "DCLG Outfit Recommender API"
    api_version: str = "1.0.0"
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "https://*.vercel.app",
        "https://dclg-outfitrec.vercel.app",
    ]

    def get_database_url(self) -> str:
        """Get database URL - prefers DATABASE_URL env var, falls back to individual vars."""
        if self.database_url:
            return self.database_url
        if self.supabase_db_host and self.supabase_db_password:
            return f"postgresql://{self.supabase_db_user}:{self.supabase_db_password}@{self.supabase_db_host}:{self.supabase_db_port}/{self.supabase_db_name}"
        raise ValueError("DATABASE_URL or individual database credentials must be set")


@lru_cache
def get_settings() -> Settings:
    return Settings()
