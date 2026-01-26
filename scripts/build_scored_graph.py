"""
Build Scored Compatibility Graph
Outputs: compatibility_graph_scored.json
"""

import json
from typing import Dict, List, Set, Any, Tuple
from collections import defaultdict
import time

# ============================================================
# CONFIGURATION
# ============================================================

WEIGHTS = {
    "color_harmony": 0.25,
    "style_similarity": 0.25,
    "formality_alignment": 0.20,
    "statement_balance": 0.15,
    "occasion_overlap": 0.10,
    "season_fit": 0.05,
}

NEUTRALS = {
    "black", "white", "gray", "grey", "beige", "cream", "navy",
    "brown", "tan", "taupe", "charcoal", "ivory", "off-white",
    "khaki", "camel", "nude", "silver", "gold", "bone", "oatmeal"
}

COLOR_FAMILIES = {
    "red": {"red", "burgundy", "maroon", "wine", "coral", "crimson", "scarlet", "rose", "berry"},
    "blue": {"blue", "navy", "cobalt", "azure", "teal", "turquoise", "aqua", "sky", "slate"},
    "green": {"green", "olive", "forest", "mint", "sage", "emerald", "lime", "teal", "eucalyptus"},
    "yellow": {"yellow", "gold", "mustard", "amber", "honey", "lemon", "cream"},
    "orange": {"orange", "coral", "peach", "tangerine", "rust", "terracotta", "copper"},
    "pink": {"pink", "blush", "rose", "magenta", "fuchsia", "salmon", "mauve", "flamingo"},
    "purple": {"purple", "violet", "lavender", "plum", "lilac", "mauve", "grape"},
    "brown": {"brown", "tan", "camel", "chocolate", "coffee", "mocha", "cognac", "cinder"},
}

COMPLEMENTARY_PAIRS = {
    frozenset({"blue", "orange"}),
    frozenset({"red", "green"}),
    frozenset({"yellow", "purple"}),
    frozenset({"pink", "green"}),
    frozenset({"navy", "orange"}),
}

ANALOGOUS_GROUPS = [
    {"red", "orange", "yellow"},
    {"yellow", "green", "blue"},
    {"blue", "purple", "pink"},
    {"pink", "red", "orange"},
]

# ============================================================
# COLOR HARMONY
# ============================================================

def normalize_color(color: str) -> str:
    if not color:
        return ""
    color = color.lower().strip()
    for modifier in ["light", "dark", "bright", "pale", "deep", "soft", "muted", "dusty"]:
        color = color.replace(modifier, "").strip()
    if "/" in color:
        color = color.split("/")[0].strip()
    return color

def get_color_family(color: str) -> str:
    color = normalize_color(color)
    if not color:
        return ""
    for family, members in COLOR_FAMILIES.items():
        if any(member in color for member in members):
            return family
    return color

def is_neutral(color: str) -> bool:
    color = normalize_color(color)
    if not color:
        return True
    return any(n in color for n in NEUTRALS)

def compute_color_harmony(product_a: dict, product_b: dict) -> float:
    vf_a = product_a["visual_features"]
    vf_b = product_b["visual_features"]

    color_a = vf_a.get("primary_color", "")
    color_b = vf_b.get("primary_color", "")

    if not color_a or not color_b:
        return 0.7

    if is_neutral(color_a) or is_neutral(color_b):
        return 1.0

    family_a = get_color_family(color_a)
    family_b = get_color_family(color_b)

    if family_a == family_b:
        return 0.95

    pair = frozenset({family_a, family_b})
    if pair in COMPLEMENTARY_PAIRS:
        return 0.80

    for group in ANALOGOUS_GROUPS:
        if family_a in group and family_b in group:
            return 0.70

    return 0.50

# ============================================================
# STYLE SIMILARITY
# ============================================================

def compute_style_similarity(product_a: dict, product_b: dict) -> float:
    vf_a = product_a["visual_features"]
    vf_b = product_b["visual_features"]

    style_a = set(vf_a.get("style", []))
    style_b = set(vf_b.get("style", []))
    aesthetics_a = set(vf_a.get("fashion_aesthetics", []))
    aesthetics_b = set(vf_b.get("fashion_aesthetics", []))

    combined_a = style_a | aesthetics_a
    combined_b = style_b | aesthetics_b

    if not combined_a or not combined_b:
        return 0.5

    intersection = combined_a & combined_b
    max_size = max(len(combined_a), len(combined_b))

    return len(intersection) / max_size

# ============================================================
# FORMALITY ALIGNMENT
# ============================================================

def compute_formality_alignment(product_a: dict, product_b: dict) -> float:
    vf_a = product_a["visual_features"]
    vf_b = product_b["visual_features"]

    score_a = vf_a.get("formality_score", 1)
    score_b = vf_b.get("formality_score", 1)

    diff = abs(score_a - score_b)

    if diff == 0:
        return 1.0
    elif diff == 1:
        return 0.75
    else:
        return 0.0

# ============================================================
# STATEMENT BALANCE
# ============================================================

def compute_statement_balance(product_a: dict, product_b: dict) -> float:
    vf_a = product_a["visual_features"]
    vf_b = product_b["visual_features"]

    statement_a = vf_a.get("statement_piece", False)
    statement_b = vf_b.get("statement_piece", False)

    if statement_a and statement_b:
        return 0.30
    elif statement_a or statement_b:
        return 1.0
    else:
        return 0.75

# ============================================================
# OCCASION OVERLAP
# ============================================================

def compute_occasion_overlap(product_a: dict, product_b: dict) -> float:
    vf_a = product_a["visual_features"]
    vf_b = product_b["visual_features"]

    occasion_a = set(vf_a.get("occasion", []))
    occasion_b = set(vf_b.get("occasion", []))

    if not occasion_a or not occasion_b:
        return 0.5

    intersection = occasion_a & occasion_b
    max_size = max(len(occasion_a), len(occasion_b))

    return len(intersection) / max_size

# ============================================================
# SEASON FIT
# ============================================================

def compute_season_fit(product_a: dict, product_b: dict) -> float:
    vf_a = product_a["visual_features"]
    vf_b = product_b["visual_features"]

    season_a = set(vf_a.get("season", []))
    season_b = set(vf_b.get("season", []))

    if not season_a or not season_b:
        return 0.5

    intersection = season_a & season_b
    max_size = max(len(season_a), len(season_b))

    return len(intersection) / max_size

# ============================================================
# COMBINED SCORE
# ============================================================

def compute_pair_score(product_a: dict, product_b: dict) -> float:
    """
    Compute weighted compatibility score between two products.
    Returns: float between 0.0 and 1.0
    """
    scores = {
        "color_harmony": compute_color_harmony(product_a, product_b),
        "style_similarity": compute_style_similarity(product_a, product_b),
        "formality_alignment": compute_formality_alignment(product_a, product_b),
        "statement_balance": compute_statement_balance(product_a, product_b),
        "occasion_overlap": compute_occasion_overlap(product_a, product_b),
        "season_fit": compute_season_fit(product_a, product_b),
    }

    total = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
    return round(total, 3)

# ============================================================
# HARD FILTERS (from existing graph builder)
# ============================================================

def has_overlap(list_a: List[str], list_b: List[str]) -> bool:
    if not list_a or not list_b:
        return False
    return bool(set(list_a) & set(list_b))

def passes_slot_filter(slot_a: str, slot_b: str) -> bool:
    if slot_a == "Accessory" or slot_b == "Accessory":
        return True
    if slot_a == slot_b:
        return False
    return True

def passes_gender_filter(gender_a: str, gender_b: str) -> bool:
    if not gender_a or not gender_b:
        return True
    if gender_a == "Unisex" or gender_b == "Unisex":
        return True
    return gender_a == gender_b

def passes_occasion_filter(occasion_a, occasion_b, slot_a, slot_b) -> bool:
    bypass_slots = {"Accessory", "Secondary Bottom"}
    if slot_a in bypass_slots or slot_b in bypass_slots:
        return True
    if "Everyday" in occasion_a or "Everyday" in occasion_b:
        return True
    return has_overlap(occasion_a, occasion_b)

def passes_season_filter(season_a, season_b, slot_a, slot_b) -> bool:
    bypass_slots = {"Accessory", "Secondary Bottom"}
    if slot_a in bypass_slots or slot_b in bypass_slots:
        return True
    return has_overlap(season_a, season_b)

def passes_formality_filter(score_a: int, score_b: int) -> bool:
    return abs(score_a - score_b) <= 1

def is_compatible(product_a: dict, product_b: dict) -> bool:
    vf_a = product_a.get("visual_features", {})
    vf_b = product_b.get("visual_features", {})

    slot_a = vf_a.get("functional_slot", "Accessory")
    slot_b = vf_b.get("functional_slot", "Accessory")

    if not passes_slot_filter(slot_a, slot_b):
        return False

    gender_a = vf_a.get("gender", "Unisex")
    gender_b = vf_b.get("gender", "Unisex")

    if not passes_gender_filter(gender_a, gender_b):
        return False

    occasion_a = vf_a.get("occasion", [])
    occasion_b = vf_b.get("occasion", [])

    if not passes_occasion_filter(occasion_a, occasion_b, slot_a, slot_b):
        return False

    season_a = vf_a.get("season", [])
    season_b = vf_b.get("season", [])

    if not passes_season_filter(season_a, season_b, slot_a, slot_b):
        return False

    formality_a = vf_a.get("formality_score", 1)
    formality_b = vf_b.get("formality_score", 1)

    if not passes_formality_filter(formality_a, formality_b):
        return False

    return True

# ============================================================
# GRAPH BUILDER
# ============================================================

def build_scored_graph(products: List[dict]) -> Tuple[dict, dict]:
    """
    Build slot-aware scored compatibility graph.

    Returns:
        graph: {sku: {slot: [{sku, score}, ...]}}
        stats: Statistics about the graph
    """
    sku_to_product = {p["sku_id"]: p for p in products}
    skus = list(sku_to_product.keys())

    # Initialize graph
    graph = {sku: defaultdict(list) for sku in skus}

    # Statistics tracking
    all_scores = []
    score_buckets = {
        "0.9-1.0": 0, "0.8-0.9": 0, "0.7-0.8": 0,
        "0.6-0.7": 0, "0.5-0.6": 0, "0.0-0.5": 0
    }

    total_pairs = len(skus) * (len(skus) - 1) // 2
    compatible_count = 0

    print(f"Processing {total_pairs:,} product pairs...")

    for i, sku_a in enumerate(skus):
        if i % 100 == 0:
            print(f"  Progress: {i}/{len(skus)} products...")

        product_a = sku_to_product[sku_a]

        for sku_b in skus[i+1:]:
            product_b = sku_to_product[sku_b]

            if is_compatible(product_a, product_b):
                compatible_count += 1

                # Compute score
                score = compute_pair_score(product_a, product_b)
                all_scores.append(score)

                # Track distribution
                if score >= 0.9:
                    score_buckets["0.9-1.0"] += 1
                elif score >= 0.8:
                    score_buckets["0.8-0.9"] += 1
                elif score >= 0.7:
                    score_buckets["0.7-0.8"] += 1
                elif score >= 0.6:
                    score_buckets["0.6-0.7"] += 1
                elif score >= 0.5:
                    score_buckets["0.5-0.6"] += 1
                else:
                    score_buckets["0.0-0.5"] += 1

                # Get slots
                slot_a = product_a["visual_features"].get("functional_slot", "Accessory")
                slot_b = product_b["visual_features"].get("functional_slot", "Accessory")

                # Add bidirectional edges (grouped by target's slot)
                graph[sku_a][slot_b].append({"sku": sku_b, "score": score})
                graph[sku_b][slot_a].append({"sku": sku_a, "score": score})

    # Sort each slot's list by score descending
    print("  Sorting by score...")
    for sku in graph:
        for slot in graph[sku]:
            graph[sku][slot].sort(key=lambda x: x["score"], reverse=True)
        # Convert defaultdict to regular dict
        graph[sku] = dict(graph[sku])

    # Compute statistics
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
    high_score_pct = sum(1 for s in all_scores if s >= 0.7) / len(all_scores) * 100 if all_scores else 0

    # Top-5 average per product
    top5_scores = []
    for sku in graph:
        product_top5 = []
        for slot_items in graph[sku].values():
            product_top5.extend([item["score"] for item in slot_items[:5]])
        if product_top5:
            top5_scores.append(sum(sorted(product_top5, reverse=True)[:5]) / min(5, len(product_top5)))

    avg_top5 = sum(top5_scores) / len(top5_scores) if top5_scores else 0

    # Slot-wise average
    slot_scores = defaultdict(list)
    for sku in graph:
        product = sku_to_product[sku]
        source_slot = product["visual_features"].get("functional_slot", "Accessory")
        for target_slot, items in graph[sku].items():
            for item in items:
                slot_scores[f"{source_slot} -> {target_slot}"].append(item["score"])

    slot_averages = {k: round(sum(v)/len(v), 3) for k, v in slot_scores.items() if v}

    stats = {
        "total_products": len(products),
        "total_edges": compatible_count,
        "avg_score": round(avg_score, 3),
        "avg_top5_score": round(avg_top5, 3),
        "high_score_pct": round(high_score_pct, 1),
        "score_distribution": score_buckets,
        "slot_averages": dict(sorted(slot_averages.items(), key=lambda x: x[1], reverse=True)[:20])
    }

    return graph, stats


def main():
    print("=" * 60)
    print("Building SCORED Compatibility Graph")
    print("=" * 60)

    # Load products
    print("\n1. Loading products...")
    with open("D:/jobmaxing/product_metadata.json", "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    products = data["products"]
    print(f"   Loaded {len(products)} products")

    # Build scored graph
    print("\n2. Building scored compatibility graph...")
    start_time = time.time()
    graph, stats = build_scored_graph(products)
    elapsed = time.time() - start_time

    print(f"\n   Completed in {elapsed:.2f} seconds")

    # Print statistics
    print("\n3. Statistics:")
    print(f"   Total products: {stats['total_products']}")
    print(f"   Total edges: {stats['total_edges']:,}")
    print(f"   Average score: {stats['avg_score']}")
    print(f"   Average top-5 score: {stats['avg_top5_score']}")
    print(f"   Pairs with score >= 0.7: {stats['high_score_pct']}%")

    print("\n   Score Distribution:")
    for bucket, count in stats["score_distribution"].items():
        pct = count / stats["total_edges"] * 100 if stats["total_edges"] > 0 else 0
        bar = "=" * int(pct / 2)
        print(f"      {bucket}: {count:>6,} ({pct:>5.1f}%) {bar}")

    print("\n   Top Slot Pair Averages:")
    for pair, avg in list(stats["slot_averages"].items())[:10]:
        print(f"      {pair}: {avg}")

    # Save graph
    print("\n4. Saving scored graph...")
    output = {
        "metadata": {
            **stats,
            "build_time_seconds": round(elapsed, 2),
            "weights": WEIGHTS
        },
        "graph": graph
    }

    with open("D:/jobmaxing/compatibility_graph_scored.json", "w", encoding="utf-8") as f:
        json.dump(output, f)

    print("   Saved to: D:/jobmaxing/compatibility_graph_scored.json")

    # Save stats separately
    with open("D:/jobmaxing/graph_stats_scored.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print("   Saved to: D:/jobmaxing/graph_stats_scored.json")

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
