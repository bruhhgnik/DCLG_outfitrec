"""
Build Compatibility Graph using Hard Filters
Outputs: compatibility_graph.json (precomputed adjacency list)
"""

import json
from typing import Dict, List, Set, Any
from itertools import combinations
import time

# Load product metadata
def load_products(filepath: str) -> List[Dict[str, Any]]:
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    return data['products']


def has_overlap(list_a: List[str], list_b: List[str]) -> bool:
    """Check if two lists share any common elements"""
    if not list_a or not list_b:
        return False
    return bool(set(list_a) & set(list_b))


def passes_slot_filter(slot_a: str, slot_b: str) -> bool:
    """
    Check if two functional slots can coexist in an outfit.

    Rules:
    - Accessories always pair with everything (including other accessories)
    - Same slot = REJECT (can't wear 2 t-shirts, 2 sneakers)
    - Allowed layering combinations:
        - Base Top + Outerwear (t-shirt under hoodie)
        - Primary Bottom + Secondary Bottom (skirt + stockings)
        - Footwear + Secondary Bottom (sneakers + socks)
    """
    # Accessories always compatible with everything
    if slot_a == "Accessory" or slot_b == "Accessory":
        return True

    # Same slot = reject
    if slot_a == slot_b:
        return False

    # Allowed layering combinations
    allowed_pairs = {
        frozenset({"Base Top", "Outerwear"}),
        frozenset({"Primary Bottom", "Secondary Bottom"}),
        frozenset({"Footwear", "Secondary Bottom"}),
    }

    pair = frozenset({slot_a, slot_b})

    # If it's an allowed pair, return True
    if pair in allowed_pairs:
        return True

    # Different slots that aren't in conflict = allowed
    # e.g., Base Top + Primary Bottom, Footwear + Outerwear, etc.
    return True


def passes_gender_filter(gender_a: str, gender_b: str) -> bool:
    """
    Check gender compatibility.

    Rules:
    - Unisex pairs with anything
    - Men pairs with Men or Unisex
    - Women pairs with Women or Unisex
    - Men + Women = REJECT
    """
    if not gender_a or not gender_b:
        return True  # Missing data = allow

    if gender_a == "Unisex" or gender_b == "Unisex":
        return True

    return gender_a == gender_b


def passes_formality_filter(score_a: int, score_b: int) -> bool:
    """
    Check formality proximity.

    Rule: abs(formality_A - formality_B) <= 1

    Scale:
    0 = Athletic
    1 = Casual
    2 = Smart Casual
    3 = Business Casual / Luxury
    4 = Formal
    """
    return abs(score_a - score_b) <= 1


def passes_occasion_filter(occasion_a: List[str], occasion_b: List[str],
                           slot_a: str, slot_b: str) -> bool:
    """
    Check occasion compatibility with wildcard logic.

    Allow if:
    - Overlap exists OR
    - "Everyday" in either list (universal wildcard) OR
    - Either item is Accessory (accessories go with everything) OR
    - Either item is Secondary Bottom (socks go with everything)
    """
    # Accessories and Secondary Bottom bypass occasion filter
    bypass_slots = {"Accessory", "Secondary Bottom"}
    if slot_a in bypass_slots or slot_b in bypass_slots:
        return True

    # "Everyday" is a universal wildcard
    if "Everyday" in occasion_a or "Everyday" in occasion_b:
        return True

    # Standard overlap check
    return has_overlap(occasion_a, occasion_b)


def passes_season_filter(season_a: List[str], season_b: List[str],
                         slot_a: str, slot_b: str) -> bool:
    """
    Check season compatibility with wildcard logic.

    Allow if:
    - Overlap exists OR
    - Either item is Accessory OR
    - Either item is Secondary Bottom
    """
    # Accessories and Secondary Bottom bypass season filter
    bypass_slots = {"Accessory", "Secondary Bottom"}
    if slot_a in bypass_slots or slot_b in bypass_slots:
        return True

    # Standard overlap check
    return has_overlap(season_a, season_b)


def is_compatible(product_a: Dict, product_b: Dict) -> bool:
    """
    Apply ALL hard filters to determine if two products are compatible.
    Returns True only if ALL conditions pass.
    """
    vf_a = product_a.get("visual_features", {})
    vf_b = product_b.get("visual_features", {})

    # 1. SLOT COMPATIBILITY
    slot_a = vf_a.get("functional_slot", "Accessory")
    slot_b = vf_b.get("functional_slot", "Accessory")

    if not passes_slot_filter(slot_a, slot_b):
        return False

    # 2. GENDER COMPATIBILITY
    gender_a = vf_a.get("gender", "Unisex")
    gender_b = vf_b.get("gender", "Unisex")

    if not passes_gender_filter(gender_a, gender_b):
        return False

    # 3. OCCASION OVERLAP (with wildcard logic)
    occasion_a = vf_a.get("occasion", [])
    occasion_b = vf_b.get("occasion", [])

    if not passes_occasion_filter(occasion_a, occasion_b, slot_a, slot_b):
        return False

    # 4. SEASON OVERLAP (with wildcard logic)
    season_a = vf_a.get("season", [])
    season_b = vf_b.get("season", [])

    if not passes_season_filter(season_a, season_b, slot_a, slot_b):
        return False

    # 5. FORMALITY PROXIMITY
    formality_a = vf_a.get("formality_score", 1)
    formality_b = vf_b.get("formality_score", 1)

    if not passes_formality_filter(formality_a, formality_b):
        return False

    return True


def build_compatibility_graph(products: List[Dict]) -> Dict[str, List[str]]:
    """
    Build adjacency list of compatible products.

    Returns: {sku_id: [list of compatible sku_ids]}
    """
    # Initialize graph with empty lists
    graph: Dict[str, List[str]] = {p["sku_id"]: [] for p in products}

    # Create SKU to product lookup
    sku_to_product = {p["sku_id"]: p for p in products}

    # Get all SKUs
    skus = list(graph.keys())
    total_pairs = len(skus) * (len(skus) - 1) // 2

    print(f"Processing {total_pairs:,} product pairs...")

    compatible_count = 0
    rejected_counts = {
        "slot": 0,
        "gender": 0,
        "occasion": 0,
        "season": 0,
        "formality": 0
    }

    # Check all pairs
    for i, sku_a in enumerate(skus):
        if i % 100 == 0:
            print(f"  Progress: {i}/{len(skus)} products processed...")

        product_a = sku_to_product[sku_a]

        for sku_b in skus[i+1:]:
            product_b = sku_to_product[sku_b]

            if is_compatible(product_a, product_b):
                # Add bidirectional edge
                graph[sku_a].append(sku_b)
                graph[sku_b].append(sku_a)
                compatible_count += 1

    return graph, compatible_count, total_pairs


def compute_stats(graph: Dict[str, List[str]], products: List[Dict]) -> Dict:
    """Compute statistics about the compatibility graph"""

    sku_to_product = {p["sku_id"]: p for p in products}

    # Basic stats
    connection_counts = [len(v) for v in graph.values()]

    # Stats by functional slot
    slot_stats = {}
    for sku, connections in graph.items():
        slot = sku_to_product[sku]["visual_features"].get("functional_slot", "Unknown")
        if slot not in slot_stats:
            slot_stats[slot] = {"count": 0, "total_connections": 0}
        slot_stats[slot]["count"] += 1
        slot_stats[slot]["total_connections"] += len(connections)

    for slot in slot_stats:
        slot_stats[slot]["avg_connections"] = round(
            slot_stats[slot]["total_connections"] / slot_stats[slot]["count"], 1
        )

    return {
        "total_products": len(graph),
        "total_edges": sum(connection_counts) // 2,
        "avg_connections_per_product": round(sum(connection_counts) / len(connection_counts), 1),
        "min_connections": min(connection_counts),
        "max_connections": max(connection_counts),
        "isolated_products": sum(1 for c in connection_counts if c == 0),
        "by_functional_slot": slot_stats
    }


def main():
    print("=" * 50)
    print("Building Compatibility Graph")
    print("=" * 50)

    # Load products
    print("\n1. Loading products...")
    products = load_products("D:/jobmaxing/product_metadata.json")
    print(f"   Loaded {len(products)} products")

    # Build graph
    print("\n2. Building compatibility graph (hard filters only)...")
    start_time = time.time()
    graph, compatible_count, total_pairs = build_compatibility_graph(products)
    elapsed = time.time() - start_time

    print(f"\n   Completed in {elapsed:.2f} seconds")
    print(f"   Compatible pairs: {compatible_count:,} / {total_pairs:,}")
    print(f"   Compatibility rate: {compatible_count/total_pairs*100:.1f}%")

    # Compute stats
    print("\n3. Computing statistics...")
    stats = compute_stats(graph, products)

    print(f"\n   Total products: {stats['total_products']}")
    print(f"   Total edges: {stats['total_edges']:,}")
    print(f"   Avg connections per product: {stats['avg_connections_per_product']}")
    print(f"   Min connections: {stats['min_connections']}")
    print(f"   Max connections: {stats['max_connections']}")
    print(f"   Isolated products (0 connections): {stats['isolated_products']}")

    print("\n   By Functional Slot:")
    for slot, data in sorted(stats["by_functional_slot"].items()):
        print(f"      {slot}: {data['count']} items, avg {data['avg_connections']} connections")

    # Save graph
    print("\n4. Saving compatibility graph...")
    output = {
        "metadata": {
            "total_products": stats["total_products"],
            "total_edges": stats["total_edges"],
            "avg_connections": stats["avg_connections_per_product"],
            "build_time_seconds": round(elapsed, 2),
            "filters_applied": [
                "functional_slot",
                "gender",
                "occasion_overlap",
                "season_overlap",
                "formality_proximity"
            ]
        },
        "graph": graph
    }

    with open("D:/jobmaxing/compatibility_graph.json", 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print("   Saved to: D:/jobmaxing/compatibility_graph.json")

    # Save stats separately
    with open("D:/jobmaxing/graph_stats.json", 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)

    print("   Saved to: D:/jobmaxing/graph_stats.json")

    print("\n" + "=" * 50)
    print("Done!")
    print("=" * 50)


if __name__ == "__main__":
    main()
