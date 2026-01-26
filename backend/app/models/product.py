from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class FunctionalSlot(str, Enum):
    BASE_TOP = "Base Top"
    OUTERWEAR = "Outerwear"
    PRIMARY_BOTTOM = "Primary Bottom"
    SECONDARY_BOTTOM = "Secondary Bottom"
    FOOTWEAR = "Footwear"
    ACCESSORY = "Accessory"


class Gender(str, Enum):
    MEN = "Men"
    WOMEN = "Women"
    UNISEX = "Unisex"


class FormalityLevel(str, Enum):
    VERY_CASUAL = "Very Casual"
    CASUAL = "Casual"
    SMART_CASUAL = "Smart Casual"
    SEMI_FORMAL = "Semi-Formal"
    FORMAL = "Formal"


class ProductBase(BaseModel):
    sku_id: str
    image_url: str
    title: Optional[str] = None
    brand: Optional[str] = None
    type: str
    category: str
    sub_category: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_colors: list[str] = []
    pattern: Optional[str] = None
    material_appearance: Optional[str] = None
    fit: Optional[str] = None
    gender: str
    design_elements: list[str] = []
    formality_level: Optional[str] = None
    versatility: Optional[str] = None
    statement_piece: bool = False
    functional_slot: str
    style: Optional[str] = None
    fashion_aesthetics: list[str] = []
    occasion: list[str] = []
    formality_score: int
    season: list[str] = []


class ProductResponse(ProductBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    sku_id: str
    image_url: str
    title: Optional[str] = None
    brand: Optional[str] = None
    type: str
    category: str
    sub_category: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_colors: list[str] = []
    pattern: Optional[str] = None
    material_appearance: Optional[str] = None
    fit: Optional[str] = None
    gender: str
    design_elements: list[str] = []
    formality_level: Optional[str] = None
    versatility: Optional[str] = None
    statement_piece: bool = False
    functional_slot: str
    style: Optional[str] = None
    fashion_aesthetics: list[str] = []
    occasion: list[str] = []
    formality_score: int
    season: list[str] = []


class CompatibleItem(BaseModel):
    sku_id: str
    score: float
    product: Optional[ProductResponse] = None


class CompatibilityResponse(BaseModel):
    source_sku: str
    slot: Optional[str] = None
    compatible_items: list[CompatibleItem]
    total_count: int


class OutfitScoreRequest(BaseModel):
    sku_ids: list[str] = Field(..., min_length=2, max_length=10)


class OutfitScoreResponse(BaseModel):
    sku_ids: list[str]
    total_score: float
    pair_scores: dict[str, float]
    average_score: float


class ProductFilter(BaseModel):
    category: Optional[str] = None
    functional_slot: Optional[str] = None
    gender: Optional[str] = None
    brand: Optional[str] = None
    primary_color: Optional[str] = None
    formality_level: Optional[str] = None
    occasion: Optional[str] = None
    season: Optional[str] = None
    style: Optional[str] = None
    min_formality_score: Optional[int] = None
    max_formality_score: Optional[int] = None


class PaginatedResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class GraphStats(BaseModel):
    total_products: int
    total_edges: int
    avg_score: float
    avg_top5_score: float
    high_score_pct: float
    score_distribution: dict[str, int]
    slot_averages: dict[str, float]


# Look Generation Models
class LookItem(BaseModel):
    """Single item in a look."""
    sku_id: str
    title: str
    brand: str
    image_url: str
    type: str
    color: str
    slot: str


class Look(BaseModel):
    """Complete outfit look."""
    id: str
    name: str
    description: str
    dimension: str
    dimension_value: str
    items: dict[str, LookItem]
    slots_filled: list[str]


class LooksResponse(BaseModel):
    """Response containing multiple generated looks."""
    base_product: ProductResponse
    looks: list[Look]
    total_looks: int
