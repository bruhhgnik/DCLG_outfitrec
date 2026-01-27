"""
Batch script to precompute looks for all products.

Usage:
    python precompute_looks.py              # Compute missing only
    python precompute_looks.py --all        # Recompute all
    python precompute_looks.py --sku SKU    # Compute for specific SKU
"""

import asyncio
import argparse
import sys
import time

sys.path.insert(0, "backend")

from app.services.product import ProductService, _get_cached_products
from app.services.compatibility import get_compatibility_graph
from app.services.look_generator import get_look_generator
from app.services.precomputed_looks import PrecomputedLooksService


async def precompute_single(sku: str, look_gen, num_looks: int = 10) -> bool:
    """Precompute looks for a single SKU. Returns True if successful."""
    try:
        base_product, looks = await look_gen.generate_looks(sku, num_looks=num_looks)

        # Convert Look objects to dicts
        looks_data = [look.to_dict() for look in looks]

        # Store in database
        await PrecomputedLooksService.store_looks(sku, base_product, looks_data)
        return True

    except Exception as e:
        print(f"  ERROR: {e}")
        return False


async def precompute_all(recompute_all: bool = False, specific_sku: str = None):
    """Precompute looks for all products."""

    print("=" * 60)
    print("PRECOMPUTING LOOKS")
    print("=" * 60)

    # Initialize services
    print("\n1. Initializing services...")
    t0 = time.perf_counter()

    # Pre-warm caches
    cache = await _get_cached_products()
    print(f"   Product cache: {len(cache)} products")

    graph = await get_compatibility_graph()
    look_gen = get_look_generator()

    # Create table if needed
    await PrecomputedLooksService.create_table()

    print(f"   Done in {(time.perf_counter() - t0):.1f}s")

    # Determine which SKUs to process
    if specific_sku:
        skus = [specific_sku]
        print(f"\n2. Processing specific SKU: {specific_sku}")
    elif recompute_all:
        skus = list(cache.keys())
        print(f"\n2. Recomputing ALL {len(skus)} products")
    else:
        skus = await PrecomputedLooksService.get_missing_skus()
        print(f"\n2. Found {len(skus)} products without precomputed looks")

    if not skus:
        print("   Nothing to do!")
        return

    # Process each SKU
    print(f"\n3. Generating looks...")
    success = 0
    failed = 0
    total = len(skus)

    for i, sku in enumerate(skus):
        # Clear compatibility cache between products to avoid memory bloat
        if i > 0 and i % 50 == 0:
            graph.clear_cache()

        t1 = time.perf_counter()
        ok = await precompute_single(sku, look_gen, num_looks=10)
        elapsed = (time.perf_counter() - t1) * 1000

        if ok:
            success += 1
            status = "OK"
        else:
            failed += 1
            status = "FAIL"

        # Progress indicator
        pct = (i + 1) / total * 100
        print(f"   [{i+1:4}/{total}] {pct:5.1f}% | {elapsed:6.0f}ms | {status} | {sku[:40]}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total processed: {total}")
    print(f"  Successful: {success}")
    print(f"  Failed: {failed}")

    # Final stats
    stats = await PrecomputedLooksService.get_stats()
    print(f"\n  Database now has {stats['total_products']} precomputed looks")
    print("=" * 60)


async def verify_consistency(sku: str):
    """Verify that precomputed looks match freshly generated ones."""
    print(f"\nVerifying consistency for {sku}...")

    look_gen = get_look_generator()
    graph = await get_compatibility_graph()

    # Clear cache to ensure fresh generation
    graph.clear_cache()

    # Get precomputed
    precomputed = await PrecomputedLooksService.get_looks(sku, num_looks=10)
    if not precomputed:
        print("  No precomputed looks found!")
        return False

    # Generate fresh
    base_product, looks = await look_gen.generate_looks(sku, num_looks=10)
    fresh_looks = [look.to_dict() for look in looks]

    # Compare
    precomputed_looks = precomputed["looks"]

    if len(precomputed_looks) != len(fresh_looks):
        print(f"  MISMATCH: {len(precomputed_looks)} precomputed vs {len(fresh_looks)} fresh")
        return False

    matches = 0
    for i, (pre, fresh) in enumerate(zip(precomputed_looks, fresh_looks)):
        pre_items = set(pre.get("items", {}).keys())
        fresh_items = set(fresh.get("items", {}).keys())

        pre_skus = {v.get("sku_id") for v in pre.get("items", {}).values()}
        fresh_skus = {v.get("sku_id") for v in fresh.get("items", {}).values()}

        if pre_skus == fresh_skus:
            matches += 1
        else:
            print(f"  Look {i+1}: MISMATCH")
            print(f"    Precomputed: {pre_skus}")
            print(f"    Fresh: {fresh_skus}")

    print(f"  {matches}/{len(precomputed_looks)} looks match exactly")
    return matches == len(precomputed_looks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Precompute looks for products")
    parser.add_argument("--all", action="store_true", help="Recompute all products")
    parser.add_argument("--sku", type=str, help="Compute for specific SKU")
    parser.add_argument("--verify", type=str, help="Verify consistency for a SKU")

    args = parser.parse_args()

    if args.verify:
        asyncio.run(verify_consistency(args.verify))
    else:
        asyncio.run(precompute_all(recompute_all=args.all, specific_sku=args.sku))
