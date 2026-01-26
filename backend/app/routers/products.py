from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import math

from app.models.product import (
    ProductResponse,
    ProductFilter,
    PaginatedResponse,
)
from app.services.product import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=PaginatedResponse)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    functional_slot: Optional[str] = None,
    gender: Optional[str] = None,
    brand: Optional[str] = None,
    primary_color: Optional[str] = None,
    formality_level: Optional[str] = None,
    occasion: Optional[str] = None,
    season: Optional[str] = None,
    style: Optional[str] = None,
    min_formality_score: Optional[int] = Query(None, ge=0, le=4),
    max_formality_score: Optional[int] = Query(None, ge=0, le=4),
):
    """Get paginated list of products with optional filters."""
    filters = ProductFilter(
        category=category,
        functional_slot=functional_slot,
        gender=gender,
        brand=brand,
        primary_color=primary_color,
        formality_level=formality_level,
        occasion=occasion,
        season=season,
        style=style,
        min_formality_score=min_formality_score,
        max_formality_score=max_formality_score,
    )

    products, total = await ProductService.get_all(page, page_size, filters)
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse(
        items=products,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/search")
async def search_products(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Search products by title or brand."""
    products = await ProductService.search(q, limit)
    return {"items": products, "count": len(products)}


@router.get("/categories")
async def get_categories():
    """Get all unique product categories."""
    categories = await ProductService.get_categories()
    return {"categories": categories}


@router.get("/brands")
async def get_brands():
    """Get all unique brands."""
    brands = await ProductService.get_brands()
    return {"brands": brands}


@router.get("/colors")
async def get_colors():
    """Get all unique primary colors."""
    colors = await ProductService.get_colors()
    return {"colors": colors}


@router.get("/{sku_id}", response_model=ProductResponse)
async def get_product(sku_id: str):
    """Get a single product by SKU ID."""
    product = await ProductService.get_by_sku(sku_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
