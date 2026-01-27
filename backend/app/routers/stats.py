from fastapi import APIRouter

from app.models.product import GraphStats
from app.services.compatibility import get_compatibility_graph
from app.database import get_db

router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get("/graph", response_model=GraphStats)
async def get_graph_stats():
    """Get compatibility graph statistics."""
    graph = await get_compatibility_graph()
    return await graph.get_stats()


@router.get("/products")
async def get_product_stats():
    """Get product inventory statistics."""
    pool = await get_db()

    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM products")

        categories = await conn.fetch(
            """
            SELECT category, COUNT(*) as count
            FROM products
            GROUP BY category
            ORDER BY count DESC
            """
        )

        slots = await conn.fetch(
            """
            SELECT functional_slot, COUNT(*) as count
            FROM products
            GROUP BY functional_slot
            ORDER BY count DESC
            """
        )

        genders = await conn.fetch(
            """
            SELECT gender, COUNT(*) as count
            FROM products
            GROUP BY gender
            ORDER BY count DESC
            """
        )

        top_brands = await conn.fetch(
            """
            SELECT brand, COUNT(*) as count
            FROM products
            WHERE brand IS NOT NULL
            GROUP BY brand
            ORDER BY count DESC
            LIMIT 10
            """
        )

        formality_dist = await conn.fetch(
            """
            SELECT formality_score, COUNT(*) as count
            FROM products
            GROUP BY formality_score
            ORDER BY formality_score
            """
        )

    return {
        "total_products": total,
        "by_category": {row["category"]: row["count"] for row in categories},
        "by_slot": {row["functional_slot"]: row["count"] for row in slots},
        "by_gender": {row["gender"]: row["count"] for row in genders},
        "top_brands": {row["brand"]: row["count"] for row in top_brands},
        "formality_distribution": {
            str(row["formality_score"]): row["count"] for row in formality_dist
        },
    }


@router.get("/config")
async def get_site_config():
    """Get site configuration including media assets."""
    # You can later change this to a Cloudinary URL or any other CDN
    # without updating the frontend
    return {
        "hero_video_url": "/videos/hero.mp4",
        # Add more configurable assets here as needed
    }


@router.get("/health")
async def health_check():
    """Check API and database health."""
    try:
        pool = await get_db()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    graph = await get_compatibility_graph()
    graph_loaded = len(graph.graph) > 0
    graph_products = len(graph.graph)

    return {
        "status": "ok" if db_status == "healthy" and graph_loaded else "degraded",
        "database": db_status,
        "compatibility_graph_loaded": graph_loaded,
        "graph_products": graph_products,
    }
