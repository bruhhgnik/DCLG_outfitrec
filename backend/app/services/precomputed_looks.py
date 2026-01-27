"""
Precomputed Looks Service
=========================

Stores and retrieves pre-generated looks for instant API responses.
"""

from typing import Optional
from app.database import get_db


class PrecomputedLooksService:
    """Service for managing precomputed looks."""

    @staticmethod
    async def create_table():
        """Create the precomputed_looks table if it doesn't exist."""
        pool = await get_db()
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS precomputed_looks (
                    sku_id TEXT PRIMARY KEY,
                    base_product JSONB NOT NULL,
                    looks JSONB NOT NULL,
                    num_looks INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            # Create index for fast lookups
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_precomputed_looks_updated
                ON precomputed_looks(updated_at DESC)
            """)
        print("precomputed_looks table ready")

    @staticmethod
    async def get_looks(sku_id: str, num_looks: int = 10) -> Optional[dict]:
        """
        Get precomputed looks for a SKU.

        Returns None if not found or if fewer looks than requested.
        """
        pool = await get_db()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT base_product, looks, num_looks
                FROM precomputed_looks
                WHERE sku_id = $1
                """,
                sku_id
            )

        if not row:
            return None

        # Check if we have enough looks
        if row["num_looks"] < num_looks:
            return None

        import json
        return {
            "base_product": json.loads(row["base_product"]) if isinstance(row["base_product"], str) else row["base_product"],
            "looks": json.loads(row["looks"]) if isinstance(row["looks"], str) else row["looks"],
        }

    @staticmethod
    async def store_looks(sku_id: str, base_product: dict, looks: list):
        """Store precomputed looks for a SKU."""
        import json
        from datetime import datetime

        def json_serializer(obj):
            """Handle datetime and other non-serializable types."""
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        pool = await get_db()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO precomputed_looks (sku_id, base_product, looks, num_looks, updated_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (sku_id) DO UPDATE SET
                    base_product = $2,
                    looks = $3,
                    num_looks = $4,
                    updated_at = NOW()
                """,
                sku_id,
                json.dumps(base_product, default=json_serializer),
                json.dumps(looks, default=json_serializer),
                len(looks)
            )

    @staticmethod
    async def delete_looks(sku_id: str):
        """Delete precomputed looks for a SKU."""
        pool = await get_db()
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM precomputed_looks WHERE sku_id = $1",
                sku_id
            )

    @staticmethod
    async def get_stats() -> dict:
        """Get statistics about precomputed looks."""
        pool = await get_db()
        async with pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM precomputed_looks")
            oldest = await conn.fetchval("SELECT MIN(updated_at) FROM precomputed_looks")
            newest = await conn.fetchval("SELECT MAX(updated_at) FROM precomputed_looks")

        return {
            "total_products": total,
            "oldest_update": str(oldest) if oldest else None,
            "newest_update": str(newest) if newest else None,
        }

    @staticmethod
    async def get_missing_skus() -> list[str]:
        """Get SKUs that don't have precomputed looks yet."""
        pool = await get_db()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT p.sku_id
                FROM products p
                LEFT JOIN precomputed_looks pl ON p.sku_id = pl.sku_id
                WHERE pl.sku_id IS NULL
                ORDER BY p.sku_id
            """)
        return [row["sku_id"] for row in rows]
