from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.models.product import (
    CompatibleItem,
    CompatibilityResponse,
    OutfitScoreRequest,
    OutfitScoreResponse,
    LooksResponse,
    Look,
    LookItem,
    ProductResponse,
)
from app.services.compatibility import get_compatibility_graph
from app.services.product import ProductService
from app.services.look_generator import get_look_generator

router = APIRouter(prefix="/outfits", tags=["Outfits"])


@router.get("/{sku_id}/compatible", response_model=CompatibilityResponse)
async def get_compatible_items(
    sku_id: str,
    slot: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    include_products: bool = Query(False),
):
    """
    Get compatible items for a given product SKU.

    - **slot**: Filter by functional slot (Base Top, Outerwear, etc.)
    - **limit**: Max items per slot
    - **min_score**: Minimum compatibility score (0.0 - 1.0)
    - **include_products**: Include full product details in response
    """
    graph = get_compatibility_graph()
    compatible = graph.get_compatible_items(sku_id, slot, limit, min_score)

    if not compatible:
        # Check if product exists
        product = await ProductService.get_by_sku(sku_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return CompatibilityResponse(
            source_sku=sku_id,
            slot=slot,
            compatible_items=[],
            total_count=0,
        )

    # Flatten all compatible items
    all_items = []
    for slot_name, items in compatible.items():
        for item in items:
            all_items.append(
                CompatibleItem(
                    sku_id=item["sku"],
                    score=item["score"],
                )
            )

    # Include product details if requested
    if include_products and all_items:
        sku_ids = [item.sku_id for item in all_items]
        products = await ProductService.get_by_skus(sku_ids)
        product_map = {p["sku_id"]: p for p in products}

        for item in all_items:
            if item.sku_id in product_map:
                item.product = product_map[item.sku_id]

    return CompatibilityResponse(
        source_sku=sku_id,
        slot=slot,
        compatible_items=all_items,
        total_count=len(all_items),
    )


@router.get("/{sku_id}/compatible/{slot}")
async def get_compatible_by_slot(
    sku_id: str,
    slot: str,
    limit: int = Query(20, ge=1, le=100),
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    include_products: bool = Query(False),
):
    """Get compatible items for a specific slot."""
    return await get_compatible_items(
        sku_id=sku_id,
        slot=slot,
        limit=limit,
        min_score=min_score,
        include_products=include_products,
    )


@router.post("/score", response_model=OutfitScoreResponse)
async def score_outfit(request: OutfitScoreRequest):
    """
    Calculate compatibility score for a set of items.

    Provide 2-10 SKU IDs to calculate pairwise compatibility scores.
    """
    # Verify all products exist
    products = await ProductService.get_by_skus(request.sku_ids)
    found_skus = {p["sku_id"] for p in products}
    missing = set(request.sku_ids) - found_skus

    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Products not found: {', '.join(missing)}",
        )

    graph = get_compatibility_graph()
    result = graph.calculate_outfit_score(request.sku_ids)

    return OutfitScoreResponse(
        sku_ids=request.sku_ids,
        total_score=result["total_score"],
        pair_scores=result["pair_scores"],
        average_score=result["average_score"],
    )


@router.post("/generate")
async def generate_outfit(
    base_sku: str,
    slots: Optional[list[str]] = Query(None),
    min_score: float = Query(0.5, ge=0.0, le=1.0),
    limit_per_slot: int = Query(5, ge=1, le=20),
):
    """
    Generate outfit recommendations starting from a base item.

    - **base_sku**: The starting item SKU
    - **slots**: Specific slots to fill (defaults to all compatible slots)
    - **min_score**: Minimum compatibility score
    - **limit_per_slot**: Max recommendations per slot
    """
    # Verify base product exists
    base_product = await ProductService.get_by_sku(base_sku)
    if not base_product:
        raise HTTPException(status_code=404, detail="Base product not found")

    graph = get_compatibility_graph()
    compatible = graph.get_compatible_items(
        base_sku, slot=None, limit=limit_per_slot, min_score=min_score
    )

    if slots:
        compatible = {k: v for k, v in compatible.items() if k in slots}

    # Fetch product details for recommendations
    all_skus = []
    for items in compatible.values():
        all_skus.extend([item["sku"] for item in items])

    products = await ProductService.get_by_skus(all_skus)
    product_map = {p["sku_id"]: p for p in products}

    recommendations = {}
    for slot_name, items in compatible.items():
        recommendations[slot_name] = [
            {
                "sku_id": item["sku"],
                "score": item["score"],
                "product": product_map.get(item["sku"]),
            }
            for item in items
        ]

    return {
        "base_product": base_product,
        "recommendations": recommendations,
        "slots_filled": list(recommendations.keys()),
    }


@router.post("/generate-looks", response_model=LooksResponse)
async def generate_looks(
    base_sku: str,
    num_looks: int = Query(10, ge=1, le=15),
):
    """
    Generate multiple complete outfit looks using the DCLG algorithm.

    This endpoint generates thematically distinct looks where each look is
    coherent within its dimension (occasion, aesthetic, color strategy).
    Looks are NOT ranked against each other - each is equally valid.

    - **base_sku**: The starting item SKU
    - **num_looks**: Number of looks to generate (1-5, default 3)

    Returns complete outfit looks with:
    - Look name and description
    - Dimension used for theming (aesthetic, occasion, color)
    - Items organized by slot (base top, outerwear, bottom, footwear, accessory)
    """
    look_generator = get_look_generator()

    try:
        base_product, looks = await look_generator.generate_looks(
            base_sku=base_sku,
            num_looks=num_looks,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Convert to response model
    response_looks = []
    for look in looks:
        look_dict = look.to_dict()
        response_looks.append(Look(
            id=look_dict["id"],
            name=look_dict["name"],
            description=look_dict["description"],
            dimension=look_dict["dimension"],
            dimension_value=look_dict["dimension_value"],
            items={
                slot: LookItem(**item_data)
                for slot, item_data in look_dict["items"].items()
            },
            slots_filled=look_dict["slots_filled"],
        ))

    return LooksResponse(
        base_product=ProductResponse(**base_product),
        looks=response_looks,
        total_looks=len(response_looks),
    )
