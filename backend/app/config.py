from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

# Get the backend directory (parent of app/)
BACKEND_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    supabase_db_host: str
    supabase_db_port: int = 5432
    supabase_db_name: str = "postgres"
    supabase_db_user: str = "postgres"
    supabase_db_password: str

    # Paths
    compatibility_graph_path: str = "compatibility_graph.json"

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

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.supabase_db_user}:{self.supabase_db_password}@{self.supabase_db_host}:{self.supabase_db_port}/{self.supabase_db_name}"

    @property
    def async_database_url(self) -> str:
        return f"postgresql+asyncpg://{self.supabase_db_user}:{self.supabase_db_password}@{self.supabase_db_host}:{self.supabase_db_port}/{self.supabase_db_name}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
