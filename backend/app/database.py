import asyncpg
from typing import Optional

from app.config import get_settings

settings = get_settings()


class Database:
    pool: Optional[asyncpg.Pool] = None

    @classmethod
    async def connect(cls):
        if cls.pool is None:
            database_url = settings.get_database_url()
            print(f"  Connecting to database...")
            cls.pool = await asyncpg.create_pool(
                database_url,
                min_size=2,
                max_size=10,
                statement_cache_size=0,  # Required for pgbouncer/transaction mode
            )

    @classmethod
    async def disconnect(cls):
        if cls.pool:
            await cls.pool.close()
            cls.pool = None

    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        if cls.pool is None:
            await cls.connect()
        return cls.pool


async def get_db() -> asyncpg.Pool:
    return await Database.get_pool()
