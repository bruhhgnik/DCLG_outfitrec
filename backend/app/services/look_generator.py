"""
Dimension-Constrained Look Generation (DCLG) Service
=====================================================

Optimized implementation with:
- O(1) pair score lookups via hash map index
- Pre-computed dimension clusters
- Cached slot normalization
- Async database integration
"""

from typing import Dict, FrozenSet, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from functools import lru_cache
import json
from pathlib import Path

from app.config import get_settings
from app.services.product import ProductService

settings = get_settings()


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

# Statement details that should remain visible - don't cover with closed outerwear
STATEMENT_DETAILS = frozenset({
    "lace", "lace trim", "cutout", "cutouts", "sweetheart neckline",
    "corset", "ruching", "embroidery", "sequin", "beading",
    "mesh panel", "sheer", "keyhole", "bow detail", "ruffles",
    "peplum", "asymmetric", "one shoulder", "off shoulder",
    "cold shoulder", "backless", "plunging neckline"
})

# Sleeve types that shouldn't be covered by closed outerwear
STATEMENT_SLEEVES = frozenset({
    "bell sleeves", "puff sleeves", "balloon sleeves", "flutter sleeves",
    "bishop sleeves", "lantern sleeves", "ruffle sleeves", "cape sleeves",
    "dolman sleeves", "kimono sleeves", "trumpet sleeves"
})

# Closed outerwear types that hide what's underneath
CLOSED_OUTERWEAR_TYPES = frozenset({
    "hoodie", "sweatshirt", "pullover", "pullover sweater",
    "crewneck sweater", "crewneck", "turtleneck", "fleece",
    "anorak", "windbreaker", "parka", "puffer", "down jacket"
})

# Outerwear design elements that make it unsuitable for traditional layering
# These are statement/styled pieces, not functional layering
STATEMENT_OUTERWEAR_ELEMENTS = frozenset({
    "off-shoulder", "off shoulder", "dropped shoulders", "one shoulder",
    "cape", "poncho", "asymmetric", "deconstructed", "cropped back"
})

# Open outerwear that allows statement pieces to show
OPEN_OUTERWEAR_TYPES = frozenset({
    "cardigan", "blazer", "jacket", "denim jacket", "leather jacket",
    "bomber jacket", "shrug", "bolero", "kimono", "duster",
    "open front", "vest", "gilet"
})

# Cropped/statement top types
STATEMENT_TOP_TYPES = frozenset({
    "crop top", "cropped top", "bustier", "corset top", "bralette",
    "tube top", "bandeau", "halter top", "cami", "camisole"
})

# Athleisure bottom types that clash with feminine/dressy tops
ATHLEISURE_BOTTOMS = frozenset({
    "sweatpants", "joggers", "track pants", "athletic shorts",
    "gym shorts", "running shorts"
})

# Feminine/dressy aesthetics that clash with athleisure
FEMININE_DRESSY_AESTHETICS = frozenset({
    "coquette", "romantic", "feminine", "elegant", "dressy",
    "glamorous", "chic", "sophisticated", "dainty", "delicate"
})

# Knitwear/sweater types - don't layer closed outerwear (hoodies) over these
KNITWEAR_TYPES = frozenset({
    "sweater", "jumper", "cardigan", "knit", "pullover sweater",
    "crewneck sweater", "turtleneck", "mock neck", "v-neck sweater"
})

# Athletic/gym top types - should only pair with athletic bottoms
ATHLETIC_TOP_TYPES = frozenset({
    "compression", "compression shirt", "compression top",
    "gym shirt", "gym top", "training top", "workout top",
    "tank top", "muscle tee", "performance top", "athletic top",
    "sports bra", "running top", "dri-fit", "dry fit"
})

# Athletic bottom types - pair with athletic tops
ATHLETIC_BOTTOM_TYPES = frozenset({
    "shorts", "athletic shorts", "gym shorts", "running shorts",
    "basketball shorts", "training shorts", "sport shorts",
    "joggers", "track pants", "sweatpants", "athletic pants",
    "training pants", "workout pants", "compression pants",
    "leggings", "tights", "running tights"
})

# Fashion/street bottom types - don't pair with pure athletic tops
FASHION_BOTTOM_TYPES = frozenset({
    "jeans", "skinny jeans", "slim jeans", "straight jeans",
    "denim", "chinos", "trousers", "dress pants", "slacks",
    "cargo pants", "cargo", "wide leg jeans", "bootcut"
})

# Streetwear aesthetics where crop top + athleisure CAN work
STREETWEAR_AESTHETICS = frozenset({
    "streetwear", "athleisure", "sporty", "athletic", "hypebeast",
    "urban", "y2k"  # Y2K sometimes mixes these
})

# Unwearable accessories - NOT part of a fashion outfit
# These are items you don't wear/carry as part of your look
UNWEARABLE_ACCESSORY_TYPES = frozenset({
    # Tech cases - not worn
    "phone case", "airpod case", "airpods case", "tablet case", "iphone case",
    "laptop case", "laptop sleeve", "earbud case", "headphone case",
    # Smoking/misc accessories
    "rolling paper", "lighter", "ashtray", "grinder", "pipe",
    # Collectibles & toys - not worn
    "sticker", "poster", "figurine", "toy", "collectible", "plush",
    "action figure", "model", "statue", "doll",
    # Home items - not worn
    "candle", "incense", "home decor", "decoration", "vase", "pillow",
    "blanket", "towel", "rug", "mat",
    # Drinkware - not worn
    "water bottle", "tumbler", "mug", "cup", "flask", "thermos",
    # Office/misc
    "notebook", "pen", "pencil", "mousepad", "coaster",
    # Keychains (debatable but not really part of outfit)
    "keychain", "key chain", "lanyard", "carabiner",
    # Fragrances - not visually part of outfit
    "perfume", "fragrance", "cologne", "eau de toilette", "eau de parfum",
    "body spray", "aftershave"
})

# Wearable accessory types that ARE part of a fashion outfit
WEARABLE_ACCESSORY_TYPES = frozenset({
    # Jewelry
    "bracelet", "necklace", "chain", "pendant", "ring", "earring", "earrings",
    "anklet", "body chain", "brooch", "pin", "lapel pin", "cufflink", "cufflinks",
    # Watches
    "watch", "smartwatch", "timepiece",
    # Headwear
    "hat", "cap", "beanie", "bucket hat", "snapback", "fitted cap", "visor",
    "beret", "fedora", "baseball cap", "dad hat", "trucker hat",
    # Eyewear
    "sunglasses", "glasses", "eyewear", "shades",
    # Bags - YES these are part of outfits!
    "bag", "backpack", "duffle", "duffel", "tote", "messenger bag", "crossbody",
    "shoulder bag", "sling bag", "fanny pack", "belt bag", "clutch", "purse",
    "handbag", "satchel", "briefcase",
    # Neckwear & headwear
    "scarf", "bandana", "headband", "hair accessory", "scrunchie",
    "neck warmer", "balaclava", "mask",
    # Belts & waist
    "belt", "suspenders", "waist chain",
    # Hand accessories
    "gloves", "mittens",
    # Formal accessories
    "tie", "bow tie", "pocket square",
    # Wallets (you carry these as part of your look)
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

    # Check if neutral
    if any(n in color_lower for n in NEUTRALS):
        return "neutral"

    # Check color families
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
    """
    Check if two color sets are harmonious.

    Harmonious means:
    - Same color family (matching)
    - Both neutral
    - One neutral + one color (neutral goes with everything)
    - Complementary colors (defined pairs)
    """
    # Empty sets are permissive
    if not colors1 or not colors2:
        return True

    # Neutrals go with everything
    if colors1 == {"neutral"} or colors2 == {"neutral"}:
        return True

    # Any overlap is good
    if colors1 & colors2:
        return True

    # Check if one side is all neutrals
    non_neutral1 = colors1 - {"neutral"}
    non_neutral2 = colors2 - {"neutral"}

    if not non_neutral1 or not non_neutral2:
        return True

    # Complementary color pairs that work together
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

    # Different non-neutral, non-complementary colors = clash
    return False


def has_overlap(list_a: List[str], list_b: List[str]) -> bool:
    """Check if two lists have any common elements."""
    if not list_a or not list_b:
        return True  # Empty lists are permissive
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
# OPTIMIZED LOOK GENERATOR
# ============================================================

class LookGeneratorService:
    """
    Optimized DCLG algorithm implementation.

    Optimizations:
    - O(1) pair score lookups via _pair_index hash map
    - Pre-indexed candidates by slot
    - Cached slot normalization
    - Single graph load with indexes built once
    """

    _instance: Optional["LookGeneratorService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._graph: Dict = {}
        self._pair_index: Dict[Tuple[str, str], float] = {}  # O(1) lookups
        self._slot_index: Dict[str, Dict[str, List[dict]]] = {}  # sku -> slot -> items
        self._metadata: Dict = {}
        self._initialized = True

    def load(self, path: Optional[str] = None):
        """Load graph and build optimized indexes."""
        if path is None:
            path = settings.compatibility_graph_path

        graph_path = Path(path)
        if not graph_path.is_absolute():
            graph_path = Path(__file__).parent.parent.parent / path

        with open(graph_path, "r") as f:
            data = json.load(f)

        self._metadata = data.get("metadata", {})
        self._graph = data.get("graph", {})

        # Build optimized indexes
        self._build_pair_index()
        self._build_slot_index()

    def _build_pair_index(self):
        """
        Build O(1) pair score lookup index.
        Maps (sku1, sku2) -> score for instant lookups.
        """
        self._pair_index = {}

        for sku1, slots in self._graph.items():
            for slot_items in slots.values():
                for item in slot_items:
                    sku2 = item["sku"]
                    score = item["score"]
                    # Store both directions for O(1) lookup either way
                    self._pair_index[(sku1, sku2)] = score
                    self._pair_index[(sku2, sku1)] = score

    def _build_slot_index(self):
        """
        Build slot-indexed structure for fast slot filtering.
        """
        self._slot_index = {}

        for sku, slots in self._graph.items():
            normalized_slots = {}
            for slot, items in slots.items():
                norm_slot = normalize_slot(slot)
                if norm_slot not in normalized_slots:
                    normalized_slots[norm_slot] = []
                normalized_slots[norm_slot].extend(items)
            self._slot_index[sku] = normalized_slots

    def get_pair_score(self, sku1: str, sku2: str) -> float:
        """O(1) pair score lookup."""
        return self._pair_index.get((sku1, sku2), 0.0)

    def get_compatible_by_slot(self, sku: str, slot: str) -> List[dict]:
        """Get compatible items for a specific slot."""
        if sku not in self._slot_index:
            return []
        return self._slot_index[sku].get(normalize_slot(slot), [])

    def get_all_compatible(self, sku: str) -> Dict[str, List[dict]]:
        """Get all compatible items indexed by slot."""
        return self._slot_index.get(sku, {})

    def _has_statement_details(self, product: dict) -> bool:
        """Check if product has statement details that should remain visible."""
        design_elements = product.get("design_elements") or []
        elements_lower = " ".join(str(e).lower() for e in design_elements)

        # Check design elements for statement details
        for detail in STATEMENT_DETAILS:
            if detail in elements_lower:
                return True

        # Check for statement sleeves
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

        # Also check aesthetics
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

        # Check for knit materials
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
        """
        Check if accessory is wearable as part of an outfit.
        Excludes bags, phone cases, home items, etc.
        """
        product_type = (product.get("type") or "").lower()
        sub_category = (product.get("sub_category") or "").lower()
        title = (product.get("title") or "").lower()

        combined = f"{product_type} {sub_category} {title}"

        # First check if it's explicitly unwearable
        for unwearable in UNWEARABLE_ACCESSORY_TYPES:
            if unwearable in combined:
                return False

        # Then check if it matches known wearable types
        for wearable in WEARABLE_ACCESSORY_TYPES:
            if wearable in combined:
                return True

        # Default: if not in unwearable list and is an accessory, allow it
        # but be conservative - if type is vague, reject
        if product_type in ["accessory", "accessories", ""]:
            # Vague type - check sub_category or title for clues
            return False

        return True

    def _is_statement_outerwear(self, product: dict) -> bool:
        """Check if outerwear has statement elements that make it unsuitable for traditional layering."""
        design_elements = product.get("design_elements") or []
        elements_lower = " ".join(str(e).lower() for e in design_elements)

        for element in STATEMENT_OUTERWEAR_ELEMENTS:
            if element in elements_lower:
                return True
        return False

    def _check_silhouette_compatibility(self, base: dict, candidate: dict) -> bool:
        """
        Check silhouette and statement piece compatibility.
        Returns False if the pairing violates fashion logic.
        """
        cand_slot = normalize_slot(candidate.get("functional_slot", ""))

        # Rule 0: Statement outerwear (off-shoulder, deconstructed) = BAD for layering
        # These are styled pieces, not traditional layering
        if cand_slot == "outerwear":
            if self._is_statement_outerwear(candidate):
                return False

        # Rule 1: Statement tops + closed outerwear = BAD
        # Don't cover statement details (lace, cutouts, special necklines)
        if cand_slot == "outerwear":
            if self._has_statement_details(base) or self._has_statement_sleeves(base):
                if self._is_closed_outerwear(candidate):
                    return False

        # Rule 1b: Knitwear/sweaters + closed outerwear (hoodies) = BAD
        # Don't layer hoodies over sweaters - too bulky
        if cand_slot == "outerwear":
            if self._is_knitwear(base):
                if self._is_closed_outerwear(candidate):
                    return False

        # Rule 2: Statement/cropped tops + athleisure bottoms = BAD
        # Unless both have streetwear aesthetic
        if cand_slot == "primary bottom":
            if self._is_statement_top(base) or self._has_statement_details(base):
                if self._is_athleisure_bottom(candidate):
                    # Allow only if base has streetwear aesthetic
                    if not self._has_streetwear_aesthetic(base):
                        return False

        # Rule 3: Feminine/dressy top + athleisure bottom = BAD
        # Style coherence - don't mix dressy with athletic
        if cand_slot == "primary bottom":
            if self._has_feminine_aesthetic(base):
                if self._is_athleisure_bottom(candidate):
                    return False

        # Rule 4: Athletic/gym tops + fashion bottoms = BAD
        # Compression shirts, gym tops should only pair with athletic bottoms
        if cand_slot == "primary bottom":
            if self._is_athletic_top(base):
                if self._is_fashion_bottom(candidate):
                    return False

        return True

    def is_valid_pair(self, base: dict, candidate: dict) -> bool:
        """Check if candidate is valid pairing with base product."""
        base_slot = normalize_slot(base.get("functional_slot", ""))
        cand_slot = normalize_slot(candidate.get("functional_slot", ""))

        # Must be different slots
        if base_slot == cand_slot:
            return False

        # Silhouette and statement piece compatibility
        if not self._check_silhouette_compatibility(base, candidate):
            return False

        # Occasion overlap (soft)
        base_occ = base.get("occasion") or []
        cand_occ = candidate.get("occasion") or []
        if base_occ and cand_occ:
            if not has_overlap(base_occ, cand_occ):
                return False

        # Formality within range (allow 1 level difference - tightened)
        base_form = base.get("formality_score", 1) or 1
        cand_form = candidate.get("formality_score", 1) or 1
        if abs(base_form - cand_form) > 1:
            return False

        # Season overlap (soft)
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

            # Add to clusters for matching occasions
            for occ in product_occasions & base_occasions:
                clusters[occ].append(sku)

            # Fallback to casual if no overlap
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

            # Add to clusters for matching aesthetics
            for aes in product_aesthetics:
                if aes in base_aesthetics or not base_aesthetics:
                    clusters[aes].append(sku)

            # Fallback
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

            # Monochrome: same color family
            if candidate_family == base_family:
                clusters["monochrome"].append(sku)

            # Neutral: neutral colors
            if candidate_family == "neutral":
                clusters["neutral"].append(sku)

            # Accent: different non-neutral color
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
        """
        Check if candidate's colors harmonize with the outfit.
        More strict for accessories, lenient for core pieces.
        """
        candidate_colors = get_all_product_colors(candidate)

        if not candidate_colors or not outfit_colors:
            return True

        # For accessories - must harmonize (no clashing accent colors)
        if slot == "accessory":
            return colors_are_harmonious(candidate_colors, outfit_colors)

        # For footwear - prefer harmony but allow some flexibility
        if slot == "footwear":
            # Neutral footwear always works
            if candidate_colors <= {"neutral"}:
                return True
            return colors_are_harmonious(candidate_colors, outfit_colors)

        # Core pieces (tops, bottoms, outerwear) - more lenient
        return True

    def select_best_for_slot(
        self,
        slot: str,
        candidates: List[str],
        current_items: Dict[str, str],  # slot -> sku
        products: Dict[str, dict],
    ) -> Optional[str]:
        """
        Select best candidate for a slot based on coherence with current look.
        Uses O(1) pair score lookups and color harmony checking.
        """
        slot_lower = normalize_slot(slot)

        # Get current outfit colors for harmony checking
        outfit_colors = self._get_outfit_colors(current_items, products)

        # Filter to candidates that match this slot
        slot_candidates = [
            sku for sku in candidates
            if sku in products and normalize_slot(products[sku].get("functional_slot", "")) == slot_lower
        ]

        if not slot_candidates:
            return None

        # For accessories and footwear, filter by color harmony first
        if slot_lower in ("accessory", "footwear") and outfit_colors:
            color_matched = [
                sku for sku in slot_candidates
                if self._check_color_harmony_with_outfit(products[sku], outfit_colors, slot_lower)
            ]
            if color_matched:
                slot_candidates = color_matched

        if not current_items:
            # First item - return highest scored from graph
            return slot_candidates[0]

        # Score each candidate by average compatibility with current look items
        best_sku = None
        best_score = -1.0

        for sku in slot_candidates:
            total_score = 0.0
            count = 0

            for existing_sku in current_items.values():
                # O(1) lookup!
                score = self.get_pair_score(sku, existing_sku)
                total_score += score
                count += 1

            avg_score = total_score / count if count > 0 else 0

            # Bonus for color harmony
            if self._check_color_harmony_with_outfit(products[sku], outfit_colors, slot_lower):
                avg_score += 0.05  # Small bonus for matching colors

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

        Returns:
            Tuple of (base_product_dict, list of Look objects)
        """
        # Fetch base product
        base_product = await ProductService.get_by_sku(base_sku)
        if not base_product:
            raise ValueError(f"Product not found: {base_sku}")

        # Get all compatible items from graph
        compatible_by_slot = self.get_all_compatible(base_sku)

        # Collect top compatible SKUs per slot (limit to reduce DB load)
        # Items are already sorted by score, so top N = best matches
        CANDIDATES_PER_SLOT = 25
        all_compatible_skus = set()
        for slot_items in compatible_by_slot.values():
            for item in slot_items[:CANDIDATES_PER_SLOT]:
                all_compatible_skus.add(item["sku"])

        if not all_compatible_skus:
            return base_product, []

        # Fetch all compatible products in single batch query
        products_list = await ProductService.get_by_skus(list(all_compatible_skus))
        products = {p["sku_id"]: p for p in products_list}
        products[base_sku] = base_product

        # Filter to valid pairs
        valid_candidates = {
            sku: p for sku, p in products.items()
            if sku != base_sku and self.is_valid_pair(base_product, p)
        }

        if not valid_candidates:
            return base_product, []

        # Cluster by dimensions
        occasion_clusters = self.cluster_by_occasion(valid_candidates, base_product)
        aesthetic_clusters = self.cluster_by_aesthetic(valid_candidates, base_product)
        color_clusters = self.cluster_by_color(valid_candidates, base_product)

        # Generate looks from different dimensions
        looks = []
        used_dimensions = set()
        used_items_per_slot: Dict[str, Set[str]] = defaultdict(set)

        # Priority order for dimension selection
        dimension_priority = [
            ("aesthetic", aesthetic_clusters),
            ("occasion", occasion_clusters),
            ("color", color_clusters),
        ]

        look_counter = 0

        # Extended look names for additional looks
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

            # Find the largest unused cluster
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

            look_counter += 1
            look = self._build_look_from_cluster(
                base_product=base_product,
                cluster_skus=best_cluster,
                all_products=products,
                dimension=best_dimension,
                dimension_value=best_value,
                used_items_per_slot=used_items_per_slot,
                look_id=f"look_{look_counter}",
            )

            # Track used items for diversity
            base_slot = normalize_slot(base_product.get("functional_slot", ""))
            for slot, item in look.items.items():
                if slot != base_slot:
                    used_items_per_slot[slot].add(item.sku_id)

            looks.append(look)
            used_dimensions.add((best_dimension, best_value))

        # Phase 2: Generate additional looks with extended names using remaining items
        all_valid_skus = list(valid_candidates.keys())
        extended_idx = 0

        while len(looks) < num_looks and extended_idx < len(extended_names):
            dimension, value, name, description = extended_names[extended_idx]
            extended_idx += 1

            # Check if we have enough unused items to make a new look
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
                continue  # Not enough diversity for a new look

            look_counter += 1
            look = self._build_look_from_cluster(
                base_product=base_product,
                cluster_skus=all_valid_skus,  # Use all valid candidates
                all_products=products,
                dimension=dimension,
                dimension_value=value,
                used_items_per_slot=used_items_per_slot,
                look_id=f"look_{look_counter}",
                custom_name=(name, description),
            )

            # Track used items for diversity
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
        dimension: str,
        dimension_value: str,
        used_items_per_slot: Dict[str, Set[str]],
        look_id: str,
        custom_name: Optional[Tuple[str, str]] = None,
    ) -> Look:
        """Build a complete look from a cluster of candidates."""

        # Generate look name and description
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

        # Slots to fill (exclude base's slot)
        slots_to_fill = [s for s in ALL_SLOTS if s != base_slot]

        # Get compatible items from graph
        compatible_by_slot = self.get_all_compatible(base_product["sku_id"])

        # Current items in look (for coherence calculation)
        current_items: Dict[str, str] = {base_slot: base_product["sku_id"]}

        for slot in slots_to_fill:
            used_in_slot = used_items_per_slot.get(slot, set())

            # Get candidates for this slot, excluding already used items
            slot_candidates = []

            # First: cluster items for this slot
            for sku in cluster_skus:
                if sku in all_products:
                    product = all_products[sku]
                    product_slot = normalize_slot(product.get("functional_slot", ""))
                    if product_slot == slot and sku not in used_in_slot:
                        # For accessories, only include wearable ones
                        if slot == "accessory" and not self._is_wearable_accessory(product):
                            continue
                        slot_candidates.append(sku)

            # If no unused cluster items, try any compatible item
            if not slot_candidates and slot in compatible_by_slot:
                for item in compatible_by_slot[slot][:50]:  # Check more for accessories
                    sku = item["sku"]
                    if sku in all_products and sku not in used_in_slot:
                        product = all_products[sku]
                        if self.is_valid_pair(base_product, product):
                            # For accessories, only include wearable ones
                            if slot == "accessory" and not self._is_wearable_accessory(product):
                                continue
                            slot_candidates.append(sku)

            # Select best candidate
            if slot_candidates:
                best_sku = self.select_best_for_slot(
                    slot, slot_candidates, current_items, all_products
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

        # Ensure footwear exists - REQUIRED for every look
        if not look.has_footwear:
            used_footwear = used_items_per_slot.get("footwear", set())
            footwear_items = compatible_by_slot.get("footwear", [])
            outfit_colors = self._get_outfit_colors(current_items, all_products)

            # First try: unused footwear with color harmony
            footwear_added = False
            for item in footwear_items[:30]:
                sku = item["sku"]
                if sku in all_products and sku not in used_footwear:
                    product = all_products[sku]
                    # Prefer color-harmonious footwear
                    if self._check_color_harmony_with_outfit(product, outfit_colors, "footwear"):
                        look.add_item(LookItem(
                            sku_id=sku,
                            title=product.get("title") or product.get("type", ""),
                            brand=product.get("brand", ""),
                            image_url=product.get("image_url", ""),
                            type=product.get("type", ""),
                            color=product.get("primary_color", ""),
                            slot="footwear",
                        ))
                        footwear_added = True
                        break

            # Second try: any unused footwear (relax color requirement)
            if not footwear_added:
                for item in footwear_items[:30]:
                    sku = item["sku"]
                    if sku in all_products and sku not in used_footwear:
                        product = all_products[sku]
                        look.add_item(LookItem(
                            sku_id=sku,
                            title=product.get("title") or product.get("type", ""),
                            brand=product.get("brand", ""),
                            image_url=product.get("image_url", ""),
                            type=product.get("type", ""),
                            color=product.get("primary_color", ""),
                            slot="footwear",
                        ))
                        footwear_added = True
                        break

            # Third try: allow reusing footwear if no unused ones available
            if not footwear_added and footwear_items:
                for item in footwear_items[:10]:
                    sku = item["sku"]
                    if sku in all_products:
                        product = all_products[sku]
                        look.add_item(LookItem(
                            sku_id=sku,
                            title=product.get("title") or product.get("type", ""),
                            brand=product.get("brand", ""),
                            image_url=product.get("image_url", ""),
                            type=product.get("type", ""),
                            color=product.get("primary_color", ""),
                            slot="footwear",
                        ))
                        break

        # Ensure accessory exists - REQUIRED for every look
        # Only include WEARABLE accessories (jewelry, hats, etc.) not bags/cases
        if not look.has_accessory:
            used_accessories = used_items_per_slot.get("accessory", set())
            accessory_items = compatible_by_slot.get("accessory", [])
            outfit_colors = self._get_outfit_colors(current_items, all_products)

            # First try: unused WEARABLE accessories with color harmony
            accessory_added = False
            for item in accessory_items[:50]:
                sku = item["sku"]
                if sku in all_products and sku not in used_accessories:
                    product = all_products[sku]
                    # Must be wearable AND color harmonious
                    if self._is_wearable_accessory(product):
                        if self._check_color_harmony_with_outfit(product, outfit_colors, "accessory"):
                            look.add_item(LookItem(
                                sku_id=sku,
                                title=product.get("title") or product.get("type", ""),
                                brand=product.get("brand", ""),
                                image_url=product.get("image_url", ""),
                                type=product.get("type", ""),
                                color=product.get("primary_color", ""),
                                slot="accessory",
                            ))
                            accessory_added = True
                            break

            # Second try: unused wearable accessory (relax color requirement)
            if not accessory_added:
                for item in accessory_items[:50]:
                    sku = item["sku"]
                    if sku in all_products and sku not in used_accessories:
                        product = all_products[sku]
                        if self._is_wearable_accessory(product):
                            look.add_item(LookItem(
                                sku_id=sku,
                                title=product.get("title") or product.get("type", ""),
                                brand=product.get("brand", ""),
                                image_url=product.get("image_url", ""),
                                type=product.get("type", ""),
                                color=product.get("primary_color", ""),
                                slot="accessory",
                            ))
                            accessory_added = True
                            break

            # Third try: allow reusing a WEARABLE accessory if no unused ones available
            if not accessory_added and accessory_items:
                for item in accessory_items[:30]:
                    sku = item["sku"]
                    if sku in all_products:
                        product = all_products[sku]
                        if self._is_wearable_accessory(product):
                            look.add_item(LookItem(
                                sku_id=sku,
                                title=product.get("title") or product.get("type", ""),
                                brand=product.get("brand", ""),
                                image_url=product.get("image_url", ""),
                                type=product.get("type", ""),
                                color=product.get("primary_color", ""),
                                slot="accessory",
                            ))
                            break

        return look


# Singleton accessor with lazy loading
_look_generator: Optional[LookGeneratorService] = None


def get_look_generator() -> LookGeneratorService:
    """Get the singleton look generator service."""
    global _look_generator
    if _look_generator is None:
        _look_generator = LookGeneratorService()
        _look_generator.load()
    return _look_generator
