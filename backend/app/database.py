import asyncpg
from contextlib import asynccontextmanager
from typing import Optional

from app.config import get_settings

settings = get_settings()


class Database:
    pool: Optional[asyncpg.Pool] = None

    @classmethod
    async def connect(cls):
        if cls.pool is None:
            cls.pool = await asyncpg.create_pool(
                host=settings.supabase_db_host,
                port=settings.supabase_db_port,
                database=settings.supabase_db_name,
                user=settings.supabase_db_user,
                password=settings.supabase_db_password,
                min_size=2,
                max_size=10,
                statement_cache_size=0,  # Required for pgbouncer transaction mode
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
