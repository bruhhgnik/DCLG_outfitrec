from typing import Optional
import asyncpg
import time

from app.database import get_db
from app.models.product import ProductFilter


# In-memory product cache with TTL
_product_cache: dict[str, dict] = {}
_cache_timestamp: float = 0
_CACHE_TTL_SECONDS = 300  # 5 minutes


async def _get_cached_products() -> dict[str, dict]:
    """Get all products with caching."""
    global _product_cache, _cache_timestamp

    now = time.time()
    if _product_cache and (now - _cache_timestamp) < _CACHE_TTL_SECONDS:
        return _product_cache

    # Refresh cache
    pool = await get_db()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM products")

    _product_cache = {row["sku_id"]: dict(row) for row in rows}
    _cache_timestamp = now
    return _product_cache


class ProductService:
    @staticmethod
    def _row_to_dict(row: asyncpg.Record) -> dict:
        """Convert database row to dict with proper handling of arrays."""
        return dict(row)

    @staticmethod
    async def get_all(
        page: int = 1,
        page_size: int = 20,
        filters: Optional[ProductFilter] = None,
    ) -> tuple[list[dict], int]:
        """Get paginated products with optional filters."""
        # Fast path: no filters = use in-memory cache
        if filters is None or not filters.has_any_filter():
            cache = await _get_cached_products()
            all_products = list(cache.values())
            total = len(all_products)
            offset = (page - 1) * page_size
            return all_products[offset:offset + page_size], total

        pool = await get_db()

        conditions = []
        params = []
        param_idx = 1

        if filters:
            if filters.category:
                conditions.append(f"category = ${param_idx}")
                params.append(filters.category)
                param_idx += 1

            if filters.functional_slot:
                conditions.append(f"functional_slot = ${param_idx}")
                params.append(filters.functional_slot)
                param_idx += 1

            if filters.gender:
                conditions.append(f"gender = ${param_idx}")
                params.append(filters.gender)
                param_idx += 1

            if filters.brand:
                conditions.append(f"brand ILIKE ${param_idx}")
                params.append(f"%{filters.brand}%")
                param_idx += 1

            if filters.primary_color:
                conditions.append(f"primary_color ILIKE ${param_idx}")
                params.append(f"%{filters.primary_color}%")
                param_idx += 1

            if filters.formality_level:
                conditions.append(f"formality_level = ${param_idx}")
                params.append(filters.formality_level)
                param_idx += 1

            if filters.occasion:
                conditions.append(f"${param_idx} = ANY(occasion)")
                params.append(filters.occasion)
                param_idx += 1

            if filters.season:
                conditions.append(f"${param_idx} = ANY(season)")
                params.append(filters.season)
                param_idx += 1

            if filters.style:
                conditions.append(f"style ILIKE ${param_idx}")
                params.append(f"%{filters.style}%")
                param_idx += 1

            if filters.min_formality_score is not None:
                conditions.append(f"formality_score >= ${param_idx}")
                params.append(filters.min_formality_score)
                param_idx += 1

            if filters.max_formality_score is not None:
                conditions.append(f"formality_score <= ${param_idx}")
                params.append(filters.max_formality_score)
                param_idx += 1

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        offset = (page - 1) * page_size

        query = f"""
            SELECT * FROM products
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([page_size, offset])

        count_query = f"SELECT COUNT(*) FROM products WHERE {where_clause}"
        count_params = params[:-2]  # Remove limit/offset params

        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            total = await conn.fetchval(count_query, *count_params)

        products = [ProductService._row_to_dict(row) for row in rows]
        return products, total

    @staticmethod
    async def get_by_sku(sku_id: str, use_cache: bool = True) -> Optional[dict]:
        """Get a single product by SKU ID."""
        if use_cache:
            cache = await _get_cached_products()
            return cache.get(sku_id)

        pool = await get_db()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM products WHERE sku_id = $1", sku_id
            )

        if row:
            return ProductService._row_to_dict(row)
        return None

    @staticmethod
    async def get_by_skus(sku_ids: list[str], use_cache: bool = True) -> list[dict]:
        """Get multiple products by SKU IDs."""
        if not sku_ids:
            return []

        if use_cache:
            cache = await _get_cached_products()
            return [cache[sku] for sku in sku_ids if sku in cache]

        pool = await get_db()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM products WHERE sku_id = ANY($1)", sku_ids
            )

        return [ProductService._row_to_dict(row) for row in rows]

    @staticmethod
    async def search(query: str, limit: int = 20) -> list[dict]:
        """Search products by title or brand."""
        pool = await get_db()

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM products
                WHERE title ILIKE $1 OR brand ILIKE $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                f"%{query}%",
                limit,
            )

        return [ProductService._row_to_dict(row) for row in rows]

    @staticmethod
    async def get_categories() -> list[str]:
        """Get all unique categories."""
        pool = await get_db()

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT category FROM products ORDER BY category"
            )

        return [row["category"] for row in rows]

    @staticmethod
    async def get_brands() -> list[str]:
        """Get all unique brands."""
        pool = await get_db()

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT brand FROM products WHERE brand IS NOT NULL ORDER BY brand"
            )

        return [row["brand"] for row in rows]

    @staticmethod
    async def get_colors() -> list[str]:
        """Get all unique primary colors."""
        pool = await get_db()

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT primary_color FROM products WHERE primary_color IS NOT NULL ORDER BY primary_color"
            )

        return [row["primary_color"] for row in rows]
