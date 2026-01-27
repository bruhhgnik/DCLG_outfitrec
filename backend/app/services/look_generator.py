"""
Dimension-Constrained Look Generation (DCLG) Service
=====================================================

Database-backed implementation with:
- Uses CompatibilityGraph service for compatibility data
- Fetches all needed data upfront (no N+1 queries)
- Pre-computed dimension clusters
- Cached slot normalization
"""

from typing import Dict, FrozenSet, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from functools import lru_cache

from app.services.product import ProductService
from app.services.compatibility import get_compatibility_graph


# ============================================================
# CONSTANTS
# ============================================================

ALL_SLOTS = ["base top", "outerwear", "primary bottom", "footwear", "accessory"]

NEUTRALS = frozenset({
    "black", "white", "gray", "grey", "beige", "cream", "navy",
    "brown", "tan", "charcoal", "ivory", "off-white", "khaki"
})

COLOR_FAMILIES = {
    "red": frozenset({"red", "burgundy", "maroon", "wine", "coral", "crimson"}),
    "blue": frozenset({"blue", "navy", "cobalt", "azure", "teal", "turquoise"}),
    "green": frozenset({"green", "olive", "forest", "mint", "sage", "emerald"}),
    "yellow": frozenset({"yellow", "gold", "mustard", "amber", "honey"}),
    "orange": frozenset({"orange", "coral", "peach", "tangerine", "rust"}),
    "pink": frozenset({"pink", "blush", "rose", "magenta", "fuchsia", "salmon"}),
    "purple": frozenset({"purple", "violet", "lavender", "plum", "lilac"}),
    "brown": frozenset({"brown", "tan", "camel", "chocolate", "coffee", "mocha"}),
}

# ============================================================
# SILHOUETTE & STATEMENT COMPATIBILITY RULES
# ============================================================

STATEMENT_DETAILS = frozenset({
    "lace", "lace trim", "cutout", "cutouts", "sweetheart neckline",
    "corset", "ruching", "embroidery", "sequin", "beading",
    "mesh panel", "sheer", "keyhole", "bow detail", "ruffles",
    "peplum", "asymmetric", "one shoulder", "off shoulder",
    "cold shoulder", "backless", "plunging neckline"
})

STATEMENT_SLEEVES = frozenset({
    "bell sleeves", "puff sleeves", "balloon sleeves", "flutter sleeves",
    "bishop sleeves", "lantern sleeves", "ruffle sleeves", "cape sleeves",
    "dolman sleeves", "kimono sleeves", "trumpet sleeves"
})

CLOSED_OUTERWEAR_TYPES = frozenset({
    "hoodie", "sweatshirt", "pullover", "pullover sweater",
    "crewneck sweater", "crewneck", "turtleneck", "fleece",
    "anorak", "windbreaker", "parka", "puffer", "down jacket"
})

STATEMENT_OUTERWEAR_ELEMENTS = frozenset({
    "off-shoulder", "off shoulder", "dropped shoulders", "one shoulder",
    "cape", "poncho", "asymmetric", "deconstructed", "cropped back"
})

OPEN_OUTERWEAR_TYPES = frozenset({
    "cardigan", "blazer", "jacket", "denim jacket", "leather jacket",
    "bomber jacket", "shrug", "bolero", "kimono", "duster",
    "open front", "vest", "gilet"
})

STATEMENT_TOP_TYPES = frozenset({
    "crop top", "cropped top", "bustier", "corset top", "bralette",
    "tube top", "bandeau", "halter top", "cami", "camisole"
})

ATHLEISURE_BOTTOMS = frozenset({
    "sweatpants", "joggers", "track pants", "athletic shorts",
    "gym shorts", "running shorts"
})

FEMININE_DRESSY_AESTHETICS = frozenset({
    "coquette", "romantic", "feminine", "elegant", "dressy",
    "glamorous", "chic", "sophisticated", "dainty", "delicate"
})

KNITWEAR_TYPES = frozenset({
    "sweater", "jumper", "cardigan", "knit", "pullover sweater",
    "crewneck sweater", "turtleneck", "mock neck", "v-neck sweater"
})

ATHLETIC_TOP_TYPES = frozenset({
    "compression", "compression shirt", "compression top",
    "gym shirt", "gym top", "training top", "workout top",
    "tank top", "muscle tee", "performance top", "athletic top",
    "sports bra", "running top", "dri-fit", "dry fit"
})

ATHLETIC_BOTTOM_TYPES = frozenset({
    "shorts", "athletic shorts", "gym shorts", "running shorts",
    "basketball shorts", "training shorts", "sport shorts",
    "joggers", "track pants", "sweatpants", "athletic pants",
    "training pants", "workout pants", "compression pants",
    "leggings", "tights", "running tights"
})

FASHION_BOTTOM_TYPES = frozenset({
    "jeans", "skinny jeans", "slim jeans", "straight jeans",
    "denim", "chinos", "trousers", "dress pants", "slacks",
    "cargo pants", "cargo", "wide leg jeans", "bootcut"
})

STREETWEAR_AESTHETICS = frozenset({
    "streetwear", "athleisure", "sporty", "athletic", "hypebeast",
    "urban", "y2k"
})

UNWEARABLE_ACCESSORY_TYPES = frozenset({
    "phone case", "airpod case", "airpods case", "tablet case", "iphone case",
    "laptop case", "laptop sleeve", "earbud case", "headphone case",
    "rolling paper", "lighter", "ashtray", "grinder", "pipe",
    "sticker", "poster", "figurine", "toy", "collectible", "plush",
    "action figure", "model", "statue", "doll",
    "candle", "incense", "home decor", "decoration", "vase", "pillow",
    "blanket", "towel", "rug", "mat",
    "water bottle", "tumbler", "mug", "cup", "flask", "thermos",
    "notebook", "pen", "pencil", "mousepad", "coaster",
    "keychain", "key chain", "lanyard", "carabiner",
    "perfume", "fragrance", "cologne", "eau de toilette", "eau de parfum",
    "body spray", "aftershave"
})

WEARABLE_ACCESSORY_TYPES = frozenset({
    "bracelet", "necklace", "chain", "pendant", "ring", "earring", "earrings",
    "anklet", "body chain", "brooch", "pin", "lapel pin", "cufflink", "cufflinks",
    "watch", "smartwatch", "timepiece",
    "hat", "cap", "beanie", "bucket hat", "snapback", "fitted cap", "visor",
    "beret", "fedora", "baseball cap", "dad hat", "trucker hat",
    "sunglasses", "glasses", "eyewear", "shades",
    "bag", "backpack", "duffle", "duffel", "tote", "messenger bag", "crossbody",
    "shoulder bag", "sling bag", "fanny pack", "belt bag", "clutch", "purse",
    "handbag", "satchel", "briefcase",
    "scarf", "bandana", "headband", "hair accessory", "scrunchie",
    "neck warmer", "balaclava", "mask",
    "belt", "suspenders", "waist chain",
    "gloves", "mittens",
    "tie", "bow tie", "pocket square",
    "wallet", "card holder", "card case", "money clip"
})

LOOK_NAMES = {
    "occasion": {
        "casual": ("Casual Day Out", "Relaxed everyday style"),
        "everyday": ("Everyday Essential", "Versatile daily wear"),
        "athletic": ("Active Lifestyle", "Ready for movement"),
        "smart casual": ("Elevated Casual", "Polished yet relaxed"),
        "work": ("Office Ready", "Professional and sharp"),
        "gym": ("Gym Session", "Performance focused"),
        "date": ("Date Night", "Impress with style"),
        "party": ("Party Ready", "Stand out from the crowd"),
        "weekend": ("Weekend Vibes", "Effortless weekend style"),
        "travel": ("Travel Ready", "Comfort meets style"),
    },
    "aesthetic": {
        "streetwear": ("Street Style", "Urban edge meets comfort"),
        "minimalist": ("Clean Minimal", "Less is more"),
        "athletic": ("Sport Luxe", "Athletic meets fashion"),
        "hypebeast": ("Hype Drop", "Statement streetwear"),
        "classic": ("Timeless Classic", "Enduring elegance"),
        "techwear": ("Tech Forward", "Functional futurism"),
        "y2k": ("Y2K Revival", "Early 2000s nostalgia"),
        "vintage": ("Retro Vibes", "Throwback style"),
        "preppy": ("Preppy Chic", "Clean cut sophistication"),
        "luxury": ("Luxury Edit", "Premium selections"),
        "urban": ("Urban Edge", "City-ready style"),
        "sporty": ("Sporty Casual", "Athletic inspired comfort"),
    },
    "color": {
        "monochrome": ("Monochrome Flow", "Single color harmony"),
        "neutral": ("Neutral Palette", "Understated tones"),
        "accent": ("Pop of Color", "Bold color accent"),
        "earth": ("Earth Tones", "Natural color palette"),
        "dark": ("Dark Mode", "Deep sophisticated tones"),
        "light": ("Light & Bright", "Fresh airy palette"),
    },
    "style": {
        "relaxed": ("Relaxed Fit", "Comfortable and easy"),
        "fitted": ("Sharp Silhouette", "Clean fitted lines"),
        "layered": ("Layered Look", "Dimension through layers"),
        "statement": ("Statement Piece", "Bold focal point"),
    }
}


# ============================================================
# CACHED UTILITIES
# ============================================================

@lru_cache(maxsize=64)
def normalize_slot(slot: str) -> str:
    """Normalize slot name to lowercase. Cached for performance."""
    return slot.lower().strip() if slot else ""


@lru_cache(maxsize=128)
def get_color_family(color: str) -> str:
    """Get the color family for a color. Cached for performance."""
    if not color:
        return "neutral"

    color_lower = color.lower()

    if any(n in color_lower for n in NEUTRALS):
        return "neutral"

    for family, members in COLOR_FAMILIES.items():
        if any(m in color_lower for m in members):
            return family

    return "other"


def get_all_product_colors(product: dict) -> Set[str]:
    """Get all colors from a product (primary + secondary/accents)."""
    colors = set()

    primary = product.get("primary_color")
    if primary:
        colors.add(get_color_family(primary))

    secondary = product.get("secondary_colors") or []
    for color in secondary:
        if color:
            colors.add(get_color_family(color))

    return colors


def colors_are_harmonious(colors1: Set[str], colors2: Set[str]) -> bool:
    """Check if two color sets are harmonious."""
    if not colors1 or not colors2:
        return True

    if colors1 == {"neutral"} or colors2 == {"neutral"}:
        return True

    if colors1 & colors2:
        return True

    non_neutral1 = colors1 - {"neutral"}
    non_neutral2 = colors2 - {"neutral"}

    if not non_neutral1 or not non_neutral2:
        return True

    COMPLEMENTARY_PAIRS = {
        ("blue", "orange"),
        ("red", "green"),
        ("yellow", "purple"),
        ("pink", "green"),
        ("blue", "brown"),
        ("red", "brown"),
    }

    for c1 in non_neutral1:
        for c2 in non_neutral2:
            if (c1, c2) in COMPLEMENTARY_PAIRS or (c2, c1) in COMPLEMENTARY_PAIRS:
                return True

    return False


def has_overlap(list_a: List[str], list_b: List[str]) -> bool:
    """Check if two lists have any common elements."""
    if not list_a or not list_b:
        return True
    return bool(set(list_a) & set(list_b))


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class LookItem:
    """Single item in a look."""
    sku_id: str
    title: str
    brand: str
    image_url: str
    type: str
    color: str
    slot: str

    def to_dict(self) -> dict:
        return {
            "sku_id": self.sku_id,
            "title": self.title,
            "brand": self.brand,
            "image_url": self.image_url,
            "type": self.type,
            "color": self.color,
            "slot": self.slot,
        }


@dataclass
class Look:
    """Complete outfit look."""
    id: str
    name: str
    description: str
    dimension: str
    dimension_value: str
    items: Dict[str, LookItem] = field(default_factory=dict)

    def add_item(self, item: LookItem):
        self.items[item.slot] = item

    @property
    def slots_filled(self) -> List[str]:
        return list(self.items.keys())

    @property
    def has_accessory(self) -> bool:
        return "accessory" in self.items

    @property
    def has_footwear(self) -> bool:
        return "footwear" in self.items

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "dimension": self.dimension,
            "dimension_value": self.dimension_value,
            "items": {slot: item.to_dict() for slot, item in self.items.items()},
            "slots_filled": self.slots_filled,
        }


# ============================================================
# LOOK GENERATOR SERVICE
# ============================================================

class LookGeneratorService:
    """
    Database-backed DCLG algorithm implementation.

    Key design:
    - Uses CompatibilityGraph service for all compatibility data
    - Fetches all needed data ONCE at start of generate_looks()
    - Passes data through functions (no re-fetching)
    - In-memory pair score lookups from pre-fetched data
    """

    _instance: Optional["LookGeneratorService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _has_statement_details(self, product: dict) -> bool:
        """Check if product has statement details that should remain visible."""
        design_elements = product.get("design_elements") or []
        elements_lower = " ".join(str(e).lower() for e in design_elements)

        for detail in STATEMENT_DETAILS:
            if detail in elements_lower:
                return True

        for sleeve in STATEMENT_SLEEVES:
            if sleeve in elements_lower:
                return True

        return False

    def _has_statement_sleeves(self, product: dict) -> bool:
        """Check if product has statement sleeves."""
        design_elements = product.get("design_elements") or []
        elements_lower = " ".join(str(e).lower() for e in design_elements)

        for sleeve in STATEMENT_SLEEVES:
            if sleeve in elements_lower:
                return True
        return False

    def _is_closed_outerwear(self, product: dict) -> bool:
        """Check if product is closed outerwear (hoodie, pullover, etc.)."""
        product_type = (product.get("type") or "").lower()
        sub_category = (product.get("sub_category") or "").lower()
        title = (product.get("title") or "").lower()

        for closed_type in CLOSED_OUTERWEAR_TYPES:
            if closed_type in product_type or closed_type in sub_category or closed_type in title:
                return True
        return False

    def _is_open_outerwear(self, product: dict) -> bool:
        """Check if product is open outerwear (cardigan, blazer, etc.)."""
        product_type = (product.get("type") or "").lower()
        sub_category = (product.get("sub_category") or "").lower()

        for open_type in OPEN_OUTERWEAR_TYPES:
            if open_type in product_type or open_type in sub_category:
                return True
        return False

    def _is_statement_top(self, product: dict) -> bool:
        """Check if product is a statement top type."""
        product_type = (product.get("type") or "").lower()
        sub_category = (product.get("sub_category") or "").lower()

        for top_type in STATEMENT_TOP_TYPES:
            if top_type in product_type or top_type in sub_category:
                return True
        return False

    def _is_athleisure_bottom(self, product: dict) -> bool:
        """Check if product is athleisure bottoms."""
        product_type = (product.get("type") or "").lower()
        sub_category = (product.get("sub_category") or "").lower()

        for bottom_type in ATHLEISURE_BOTTOMS:
            if bottom_type in product_type or bottom_type in sub_category:
                return True
        return False

    def _has_feminine_aesthetic(self, product: dict) -> bool:
        """Check if product has feminine/dressy aesthetics."""
        aesthetics = product.get("fashion_aesthetics") or []
        aesthetics_lower = set(a.lower() for a in aesthetics)
        return bool(aesthetics_lower & FEMININE_DRESSY_AESTHETICS)

    def _has_streetwear_aesthetic(self, product: dict) -> bool:
        """Check if product has streetwear aesthetics."""
        aesthetics = product.get("fashion_aesthetics") or []
        aesthetics_lower = set(a.lower() for a in aesthetics)
        return bool(aesthetics_lower & STREETWEAR_AESTHETICS)

    def _is_athletic_top(self, product: dict) -> bool:
        """Check if product is an athletic/gym top."""
        product_type = (product.get("type") or "").lower()
        sub_category = (product.get("sub_category") or "").lower()
        title = (product.get("title") or "").lower()
        combined = f"{product_type} {sub_category} {title}"

        for athletic_type in ATHLETIC_TOP_TYPES:
            if athletic_type in combined:
                return True

        aesthetics = product.get("fashion_aesthetics") or []
        aesthetics_lower = set(a.lower() for a in aesthetics)
        if "gym" in aesthetics_lower or "fitness" in aesthetics_lower:
            return True

        return False

    def _is_knitwear(self, product: dict) -> bool:
        """Check if product is knitwear/sweater."""
        product_type = (product.get("type") or "").lower()
        sub_category = (product.get("sub_category") or "").lower()
        material = (product.get("material_appearance") or "").lower()

        combined = f"{product_type} {sub_category} {material}"

        for knit_type in KNITWEAR_TYPES:
            if knit_type in combined:
                return True

        if "knit" in material or "wool" in material or "cashmere" in material:
            return True

        return False

    def _is_athletic_bottom(self, product: dict) -> bool:
        """Check if product is athletic bottoms."""
        product_type = (product.get("type") or "").lower()
        sub_category = (product.get("sub_category") or "").lower()
        title = (product.get("title") or "").lower()
        combined = f"{product_type} {sub_category} {title}"

        for athletic_type in ATHLETIC_BOTTOM_TYPES:
            if athletic_type in combined:
                return True
        return False

    def _is_fashion_bottom(self, product: dict) -> bool:
        """Check if product is fashion/street bottoms (jeans, chinos, etc.)."""
        product_type = (product.get("type") or "").lower()
        sub_category = (product.get("sub_category") or "").lower()
        title = (product.get("title") or "").lower()
        combined = f"{product_type} {sub_category} {title}"

        for fashion_type in FASHION_BOTTOM_TYPES:
            if fashion_type in combined:
                return True
        return False

    def _is_wearable_accessory(self, product: dict) -> bool:
        """Check if accessory is wearable as part of an outfit."""
        product_type = (product.get("type") or "").lower()
        sub_category = (product.get("sub_category") or "").lower()
        title = (product.get("title") or "").lower()

        combined = f"{product_type} {sub_category} {title}"

        for unwearable in UNWEARABLE_ACCESSORY_TYPES:
            if unwearable in combined:
                return False

        for wearable in WEARABLE_ACCESSORY_TYPES:
            if wearable in combined:
                return True

        if product_type in ["accessory", "accessories", ""]:
            return False

        return True

    def _is_statement_outerwear(self, product: dict) -> bool:
        """Check if outerwear has statement elements."""
        design_elements = product.get("design_elements") or []
        elements_lower = " ".join(str(e).lower() for e in design_elements)

        for element in STATEMENT_OUTERWEAR_ELEMENTS:
            if element in elements_lower:
                return True
        return False

    def _check_silhouette_compatibility(self, base: dict, candidate: dict) -> bool:
        """Check silhouette and statement piece compatibility."""
        cand_slot = normalize_slot(candidate.get("functional_slot", ""))

        if cand_slot == "outerwear":
            if self._is_statement_outerwear(candidate):
                return False

        if cand_slot == "outerwear":
            if self._has_statement_details(base) or self._has_statement_sleeves(base):
                if self._is_closed_outerwear(candidate):
                    return False

        if cand_slot == "outerwear":
            if self._is_knitwear(base):
                if self._is_closed_outerwear(candidate):
                    return False

        if cand_slot == "primary bottom":
            if self._is_statement_top(base) or self._has_statement_details(base):
                if self._is_athleisure_bottom(candidate):
                    # Exception: athletic tops with functional "statement" details
                    # (like mesh panels for breathability) should pair with athleisure
                    if self._is_athletic_top(base):
                        pass  # Allow athletic + athleisure pairing
                    elif not self._has_streetwear_aesthetic(base):
                        return False

        if cand_slot == "primary bottom":
            if self._has_feminine_aesthetic(base):
                if self._is_athleisure_bottom(candidate):
                    return False

        if cand_slot == "primary bottom":
            if self._is_athletic_top(base):
                if self._is_fashion_bottom(candidate):
                    return False

        return True

    def is_valid_pair(self, base: dict, candidate: dict) -> bool:
        """Check if candidate is valid pairing with base product."""
        base_slot = normalize_slot(base.get("functional_slot", ""))
        cand_slot = normalize_slot(candidate.get("functional_slot", ""))

        if base_slot == cand_slot:
            return False

        if not self._check_silhouette_compatibility(base, candidate):
            return False

        base_occ = base.get("occasion") or []
        cand_occ = candidate.get("occasion") or []
        if base_occ and cand_occ:
            if not has_overlap(base_occ, cand_occ):
                return False

        base_form = base.get("formality_score", 1) or 1
        cand_form = candidate.get("formality_score", 1) or 1
        if abs(base_form - cand_form) > 1:
            return False

        base_season = base.get("season") or []
        cand_season = candidate.get("season") or []
        if base_season and cand_season:
            if not has_overlap(base_season, cand_season):
                return False

        return True

    def cluster_by_occasion(
        self,
        candidates: Dict[str, dict],
        base: dict
    ) -> Dict[str, List[str]]:
        """Cluster candidates by occasion."""
        clusters = defaultdict(list)
        base_occasions = set(o.lower() for o in (base.get("occasion") or ["casual"]))

        for sku, product in candidates.items():
            product_occasions = set(
                o.lower() for o in (product.get("occasion") or ["casual"])
            )

            for occ in product_occasions & base_occasions:
                clusters[occ].append(sku)

            if not (product_occasions & base_occasions):
                if "casual" in base_occasions or "everyday" in base_occasions:
                    clusters["casual"].append(sku)

        return dict(clusters)

    def cluster_by_aesthetic(
        self,
        candidates: Dict[str, dict],
        base: dict
    ) -> Dict[str, List[str]]:
        """Cluster candidates by fashion aesthetic."""
        clusters = defaultdict(list)
        base_aesthetics = set(
            a.lower() for a in (base.get("fashion_aesthetics") or ["streetwear"])
        )

        for sku, product in candidates.items():
            product_aesthetics = set(
                a.lower() for a in (product.get("fashion_aesthetics") or [])
            )

            for aes in product_aesthetics:
                if aes in base_aesthetics or not base_aesthetics:
                    clusters[aes].append(sku)

            if not product_aesthetics and base_aesthetics:
                clusters[list(base_aesthetics)[0]].append(sku)

        return dict(clusters)

    def cluster_by_color(
        self,
        candidates: Dict[str, dict],
        base: dict
    ) -> Dict[str, List[str]]:
        """Cluster candidates by color strategy."""
        clusters = {
            "monochrome": [],
            "neutral": [],
            "accent": [],
        }

        base_family = get_color_family(base.get("primary_color", ""))

        for sku, product in candidates.items():
            candidate_family = get_color_family(product.get("primary_color", ""))

            if candidate_family == base_family:
                clusters["monochrome"].append(sku)

            if candidate_family == "neutral":
                clusters["neutral"].append(sku)

            if candidate_family != "neutral" and candidate_family != base_family:
                clusters["accent"].append(sku)

        return clusters

    def _get_outfit_colors(self, current_items: Dict[str, str], products: Dict[str, dict]) -> Set[str]:
        """Get all color families present in the current outfit."""
        outfit_colors = set()
        for sku in current_items.values():
            if sku in products:
                outfit_colors |= get_all_product_colors(products[sku])
        return outfit_colors

    def _check_color_harmony_with_outfit(
        self,
        candidate: dict,
        outfit_colors: Set[str],
        slot: str
    ) -> bool:
        """Check if candidate's colors harmonize with the outfit."""
        candidate_colors = get_all_product_colors(candidate)

        if not candidate_colors or not outfit_colors:
            return True

        if slot == "accessory":
            return colors_are_harmonious(candidate_colors, outfit_colors)

        if slot == "footwear":
            if candidate_colors <= {"neutral"}:
                return True
            return colors_are_harmonious(candidate_colors, outfit_colors)

        return True

    def select_best_for_slot(
        self,
        slot: str,
        candidates: List[str],
        current_items: Dict[str, str],
        products: Dict[str, dict],
        pair_scores: Dict[Tuple[str, str], float],
    ) -> Optional[str]:
        """
        Select best candidate for a slot based on coherence with current look.
        Uses pre-fetched pair scores (no database calls).
        """
        slot_lower = normalize_slot(slot)

        outfit_colors = self._get_outfit_colors(current_items, products)

        slot_candidates = [
            sku for sku in candidates
            if sku in products and normalize_slot(products[sku].get("functional_slot", "")) == slot_lower
        ]

        if not slot_candidates:
            return None

        if slot_lower in ("accessory", "footwear") and outfit_colors:
            color_matched = [
                sku for sku in slot_candidates
                if self._check_color_harmony_with_outfit(products[sku], outfit_colors, slot_lower)
            ]
            if color_matched:
                slot_candidates = color_matched

        if not current_items:
            return slot_candidates[0]

        best_sku = None
        best_score = -1.0

        for sku in slot_candidates:
            total_score = 0.0
            count = 0

            for existing_sku in current_items.values():
                # Use pre-fetched pair scores (O(1) lookup)
                score = pair_scores.get((sku, existing_sku), 0.0)
                if score == 0.0:
                    score = pair_scores.get((existing_sku, sku), 0.0)
                total_score += score
                count += 1

            avg_score = total_score / count if count > 0 else 0

            if self._check_color_harmony_with_outfit(products[sku], outfit_colors, slot_lower):
                avg_score += 0.05

            if avg_score > best_score:
                best_score = avg_score
                best_sku = sku

        return best_sku

    async def generate_looks(
        self,
        base_sku: str,
        num_looks: int = 3,
    ) -> Tuple[dict, List[Look]]:
        """
        Generate multiple thematically distinct looks for a base product.

        Key optimization: Fetch ALL data upfront in ONE query, then process in-memory.
        """
        # 1. Fetch base product
        base_product = await ProductService.get_by_sku(base_sku)
        if not base_product:
            raise ValueError(f"Product not found: {base_sku}")

        # Handle image_url field (DB stores as image_file)
        if "image_url" not in base_product and "image_file" in base_product:
            base_product["image_url"] = base_product["image_file"]

        # 2. Get compatibility graph and fetch compatible items + cross-scores in ONE query
        CANDIDATES_PER_SLOT = 25
        graph = await get_compatibility_graph()
        compatible_by_slot, pair_scores = await graph.get_compatible_with_cross_scores(
            base_sku, candidates_per_slot=CANDIDATES_PER_SLOT
        )

        # 3. Collect all compatible SKUs
        all_compatible_skus = set()
        for slot_items in compatible_by_slot.values():
            for item in slot_items:
                all_compatible_skus.add(item["sku"])

        if not all_compatible_skus:
            return base_product, []

        # 4. Fetch all compatible products in ONE batch query
        products_list = await ProductService.get_by_skus(list(all_compatible_skus))
        products = {}
        for p in products_list:
            # Handle image_url field
            if "image_url" not in p and "image_file" in p:
                p["image_url"] = p["image_file"]
            products[p["sku_id"]] = p
        products[base_sku] = base_product

        # 6. Filter to valid pairs
        valid_candidates = {
            sku: p for sku, p in products.items()
            if sku != base_sku and self.is_valid_pair(base_product, p)
        }

        if not valid_candidates:
            return base_product, []

        # 7. Cluster by dimensions (all in-memory)
        occasion_clusters = self.cluster_by_occasion(valid_candidates, base_product)
        aesthetic_clusters = self.cluster_by_aesthetic(valid_candidates, base_product)
        color_clusters = self.cluster_by_color(valid_candidates, base_product)

        # Build a global score map for sorting cluster SKUs by base compatibility
        # This ensures deterministic iteration order matching the old JSON-based code
        sku_base_score: Dict[str, float] = {}
        for slot_items in compatible_by_slot.values():
            for item in slot_items:
                if item["sku"] not in sku_base_score:
                    sku_base_score[item["sku"]] = item["score"]

        # Sort valid_candidates by base score before clustering
        # This ensures clusters are built with items in score order (matching old behavior)
        sorted_valid_skus = sorted(valid_candidates.keys(), key=lambda sku: (-sku_base_score.get(sku, 0), sku))
        valid_candidates = {sku: valid_candidates[sku] for sku in sorted_valid_skus}

        # 8. Generate looks from different dimensions
        looks = []
        used_dimensions = set()
        used_items_per_slot: Dict[str, Set[str]] = defaultdict(set)

        dimension_priority = [
            ("aesthetic", aesthetic_clusters),
            ("occasion", occasion_clusters),
            ("color", color_clusters),
        ]

        look_counter = 0

        extended_names = [
            ("style", "relaxed", "Relaxed Fit", "Comfortable and easy"),
            ("style", "fitted", "Sharp Silhouette", "Clean fitted lines"),
            ("style", "layered", "Layered Look", "Dimension through layers"),
            ("style", "statement", "Statement Piece", "Bold focal point"),
            ("color", "earth", "Earth Tones", "Natural color palette"),
            ("color", "dark", "Dark Mode", "Deep sophisticated tones"),
            ("aesthetic", "urban", "Urban Edge", "City-ready style"),
            ("aesthetic", "sporty", "Sporty Casual", "Athletic inspired comfort"),
            ("occasion", "weekend", "Weekend Vibes", "Effortless weekend style"),
            ("occasion", "travel", "Travel Ready", "Comfort meets style"),
        ]

        # Phase 1: Use unique dimension+value combinations
        while len(looks) < num_looks:
            best_cluster = None
            best_dimension = None
            best_value = None
            best_size = 0

            for dimension, clusters in dimension_priority:
                for value, skus in clusters.items():
                    if (dimension, value) in used_dimensions:
                        continue
                    if len(skus) > best_size:
                        best_size = len(skus)
                        best_cluster = skus
                        best_dimension = dimension
                        best_value = value

            if not best_cluster:
                break

            # Sort cluster SKUs by base score (descending) then alphabetically
            # This ensures deterministic order matching old code behavior
            sorted_cluster = sorted(best_cluster, key=lambda sku: (-sku_base_score.get(sku, 0), sku))

            look_counter += 1
            look = self._build_look_from_cluster(
                base_product=base_product,
                cluster_skus=sorted_cluster,
                all_products=products,
                compatible_by_slot=compatible_by_slot,
                pair_scores=pair_scores,
                dimension=best_dimension,
                dimension_value=best_value,
                used_items_per_slot=used_items_per_slot,
                look_id=f"look_{look_counter}",
            )

            base_slot = normalize_slot(base_product.get("functional_slot", ""))
            for slot, item in look.items.items():
                if slot != base_slot:
                    used_items_per_slot[slot].add(item.sku_id)

            looks.append(look)
            used_dimensions.add((best_dimension, best_value))

        # Phase 2: Generate additional looks with extended names
        # Sort by base score for deterministic order
        all_valid_skus = sorted(valid_candidates.keys(), key=lambda sku: (-sku_base_score.get(sku, 0), sku))
        extended_idx = 0

        while len(looks) < num_looks and extended_idx < len(extended_names):
            dimension, value, name, description = extended_names[extended_idx]
            extended_idx += 1

            can_fill_slots = 0
            for slot in ALL_SLOTS:
                if slot == normalize_slot(base_product.get("functional_slot", "")):
                    continue
                used_in_slot = used_items_per_slot.get(slot, set())
                available = [
                    sku for sku in all_valid_skus
                    if sku not in used_in_slot and
                    normalize_slot(products[sku].get("functional_slot", "")) == slot
                ]
                if available:
                    can_fill_slots += 1

            if can_fill_slots < 2:
                continue

            look_counter += 1
            look = self._build_look_from_cluster(
                base_product=base_product,
                cluster_skus=all_valid_skus,
                all_products=products,
                compatible_by_slot=compatible_by_slot,
                pair_scores=pair_scores,
                dimension=dimension,
                dimension_value=value,
                used_items_per_slot=used_items_per_slot,
                look_id=f"look_{look_counter}",
                custom_name=(name, description),
            )

            base_slot = normalize_slot(base_product.get("functional_slot", ""))
            for slot, item in look.items.items():
                if slot != base_slot:
                    used_items_per_slot[slot].add(item.sku_id)

            looks.append(look)

        return base_product, looks

    def _build_look_from_cluster(
        self,
        base_product: dict,
        cluster_skus: List[str],
        all_products: Dict[str, dict],
        compatible_by_slot: Dict[str, List[dict]],
        pair_scores: Dict[Tuple[str, str], float],
        dimension: str,
        dimension_value: str,
        used_items_per_slot: Dict[str, Set[str]],
        look_id: str,
        custom_name: Optional[Tuple[str, str]] = None,
    ) -> Look:
        """Build a complete look from a cluster of candidates (no database calls)."""

        if custom_name:
            name, description = custom_name
        else:
            name_data = LOOK_NAMES.get(dimension, {}).get(
                dimension_value.lower(),
                (f"{dimension_value.title()} Look", f"A {dimension_value.lower()} focused outfit")
            )
            name, description = name_data

        look = Look(
            id=look_id,
            name=name,
            description=description,
            dimension=dimension,
            dimension_value=dimension_value,
        )

        # Add base product
        base_slot = normalize_slot(base_product.get("functional_slot", ""))
        look.add_item(LookItem(
            sku_id=base_product["sku_id"],
            title=base_product.get("title") or base_product.get("type", ""),
            brand=base_product.get("brand", ""),
            image_url=base_product.get("image_url", ""),
            type=base_product.get("type", ""),
            color=base_product.get("primary_color", ""),
            slot=base_slot,
        ))

        slots_to_fill = [s for s in ALL_SLOTS if s != base_slot]
        current_items: Dict[str, str] = {base_slot: base_product["sku_id"]}

        for slot in slots_to_fill:
            used_in_slot = used_items_per_slot.get(slot, set())

            slot_candidates = []

            for sku in cluster_skus:
                if sku in all_products:
                    product = all_products[sku]
                    product_slot = normalize_slot(product.get("functional_slot", ""))
                    if product_slot == slot and sku not in used_in_slot:
                        if slot == "accessory" and not self._is_wearable_accessory(product):
                            continue
                        slot_candidates.append(sku)

            if not slot_candidates and slot in compatible_by_slot:
                for item in compatible_by_slot[slot][:50]:
                    sku = item["sku"]
                    if sku in all_products and sku not in used_in_slot:
                        product = all_products[sku]
                        if self.is_valid_pair(base_product, product):
                            if slot == "accessory" and not self._is_wearable_accessory(product):
                                continue
                            slot_candidates.append(sku)

            if slot_candidates:
                # Sort candidates by base compatibility score (from compatible_by_slot)
                # This ensures deterministic tie-breaking when cross-scores are equal
                slot_score_map = {item["sku"]: item["score"] for item in compatible_by_slot.get(slot, [])}
                slot_candidates.sort(key=lambda sku: (-slot_score_map.get(sku, 0), sku))

                best_sku = self.select_best_for_slot(
                    slot, slot_candidates, current_items, all_products, pair_scores
                )
                if best_sku and best_sku in all_products:
                    product = all_products[best_sku]
                    look.add_item(LookItem(
                        sku_id=best_sku,
                        title=product.get("title") or product.get("type", ""),
                        brand=product.get("brand", ""),
                        image_url=product.get("image_url", ""),
                        type=product.get("type", ""),
                        color=product.get("primary_color", ""),
                        slot=slot,
                    ))
                    current_items[slot] = best_sku

        # Ensure footwear exists
        if not look.has_footwear:
            self._add_required_slot(
                look, "footwear", compatible_by_slot, all_products,
                used_items_per_slot, current_items
            )

        # Ensure accessory exists
        if not look.has_accessory:
            self._add_required_slot(
                look, "accessory", compatible_by_slot, all_products,
                used_items_per_slot, current_items, require_wearable=True
            )

        return look

    def _add_required_slot(
        self,
        look: Look,
        slot: str,
        compatible_by_slot: Dict[str, List[dict]],
        all_products: Dict[str, dict],
        used_items_per_slot: Dict[str, Set[str]],
        current_items: Dict[str, str],
        require_wearable: bool = False,
    ):
        """Add a required item (footwear/accessory) to the look."""
        used_items = used_items_per_slot.get(slot, set())
        slot_items = compatible_by_slot.get(slot, [])
        outfit_colors = self._get_outfit_colors(current_items, all_products)

        added = False

        # First try: unused items with color harmony
        for item in slot_items[:30]:
            sku = item["sku"]
            if sku in all_products and sku not in used_items:
                product = all_products[sku]
                if require_wearable and not self._is_wearable_accessory(product):
                    continue
                if self._check_color_harmony_with_outfit(product, outfit_colors, slot):
                    look.add_item(LookItem(
                        sku_id=sku,
                        title=product.get("title") or product.get("type", ""),
                        brand=product.get("brand", ""),
                        image_url=product.get("image_url", ""),
                        type=product.get("type", ""),
                        color=product.get("primary_color", ""),
                        slot=slot,
                    ))
                    added = True
                    break

        # Second try: unused items (relax color)
        if not added:
            for item in slot_items[:30]:
                sku = item["sku"]
                if sku in all_products and sku not in used_items:
                    product = all_products[sku]
                    if require_wearable and not self._is_wearable_accessory(product):
                        continue
                    look.add_item(LookItem(
                        sku_id=sku,
                        title=product.get("title") or product.get("type", ""),
                        brand=product.get("brand", ""),
                        image_url=product.get("image_url", ""),
                        type=product.get("type", ""),
                        color=product.get("primary_color", ""),
                        slot=slot,
                    ))
                    added = True
                    break

        # Third try: allow reuse
        if not added and slot_items:
            for item in slot_items[:10]:
                sku = item["sku"]
                if sku in all_products:
                    product = all_products[sku]
                    if require_wearable and not self._is_wearable_accessory(product):
                        continue
                    look.add_item(LookItem(
                        sku_id=sku,
                        title=product.get("title") or product.get("type", ""),
                        brand=product.get("brand", ""),
                        image_url=product.get("image_url", ""),
                        type=product.get("type", ""),
                        color=product.get("primary_color", ""),
                        slot=slot,
                    ))
                    break


# Singleton accessor
_look_generator: Optional[LookGeneratorService] = None


def get_look_generator() -> LookGeneratorService:
    """Get the singleton look generator service."""
    global _look_generator
    if _look_generator is None:
        _look_generator = LookGeneratorService()
    return _look_generator
