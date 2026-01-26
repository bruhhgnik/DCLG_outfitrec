"""
Fix SKU Slashes Script
======================
Replaces all forward slashes (/) in SKU IDs with underscores (_).

Updates:
1. Supabase PostgreSQL database (products table)
2. compatibility_graph_scored.json
3. product_metadata.json (if exists)
"""

import json
import os
import re
import logging
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

import psycopg2

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger(__name__)

# Database config
DB_HOST = os.getenv("SUPABASE_DB_HOST", "localhost")
DB_PORT = os.getenv("SUPABASE_DB_PORT", "5432")
DB_NAME = os.getenv("SUPABASE_DB_NAME", "postgres")
DB_USER = os.getenv("SUPABASE_DB_USER", "postgres")
DB_PASS = os.getenv("SUPABASE_DB_PASSWORD", "")


def fix_database_skus():
    """Fix SKUs with slashes in the database."""
    log.info("Connecting to database...")

    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

    try:
        with conn.cursor() as cur:
            # Find all SKUs with slashes
            cur.execute("SELECT sku_id FROM products WHERE sku_id LIKE '%/%'")
            rows = cur.fetchall()

            if not rows:
                log.info("No SKUs with slashes found in database")
                return 0

            log.info(f"Found {len(rows)} SKUs with slashes in database")

            # Update each SKU
            updated = 0
            for (old_sku,) in rows:
                new_sku = old_sku.replace("/", "_")
                log.info(f"  Updating: {old_sku} -> {new_sku}")

                try:
                    cur.execute(
                        "UPDATE products SET sku_id = %s WHERE sku_id = %s",
                        (new_sku, old_sku)
                    )
                    updated += 1
                except psycopg2.Error as e:
                    log.error(f"  Failed to update {old_sku}: {e}")
                    conn.rollback()
                    continue

            conn.commit()
            log.info(f"Updated {updated} SKUs in database")
            return updated

    finally:
        conn.close()


def fix_json_file(filepath: str) -> int:
    """Fix SKUs with slashes in a JSON file."""
    if not os.path.exists(filepath):
        log.info(f"File not found: {filepath}")
        return 0

    log.info(f"Processing: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Count occurrences before
    slash_pattern = r'"([A-Za-z0-9\-]+)/([A-Za-z0-9\-]+)"'
    matches_before = re.findall(slash_pattern, content)

    if not matches_before:
        log.info(f"  No SKUs with slashes found")
        return 0

    log.info(f"  Found {len(matches_before)} potential SKU patterns with slashes")

    # Replace slashes with underscores in SKU patterns
    # Pattern matches: "XXX-XXX/YYY-YYY" format
    def replace_sku_slash(match):
        return f'"{match.group(1)}_{match.group(2)}"'

    new_content = re.sub(slash_pattern, replace_sku_slash, content)

    # Write back
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    log.info(f"  Fixed {len(matches_before)} SKU patterns")
    return len(matches_before)


def fix_compatibility_graph(filepath: str) -> int:
    """Fix SKUs in the compatibility graph JSON."""
    if not os.path.exists(filepath):
        log.info(f"File not found: {filepath}")
        return 0

    log.info(f"Processing compatibility graph: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    graph = data.get("graph", {})
    fixed_count = 0
    new_graph = {}

    for sku, slots in graph.items():
        # Fix the main SKU key
        new_sku = sku.replace("/", "_") if "/" in sku else sku
        if new_sku != sku:
            fixed_count += 1
            log.info(f"  Fixed key: {sku} -> {new_sku}")

        # Fix SKUs in the slot arrays
        new_slots = {}
        for slot_name, items in slots.items():
            new_items = []
            for item in items:
                if isinstance(item, dict) and "sku" in item:
                    old_item_sku = item["sku"]
                    new_item_sku = old_item_sku.replace("/", "_") if "/" in old_item_sku else old_item_sku
                    if new_item_sku != old_item_sku:
                        fixed_count += 1
                    item["sku"] = new_item_sku
                new_items.append(item)
            new_slots[slot_name] = new_items

        new_graph[new_sku] = new_slots

    data["graph"] = new_graph

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    log.info(f"  Fixed {fixed_count} SKU references in graph")
    return fixed_count


def main():
    log.info("=" * 60)
    log.info("SKU SLASH FIX SCRIPT")
    log.info("=" * 60)

    total_fixed = 0

    # Fix database
    try:
        total_fixed += fix_database_skus()
    except Exception as e:
        log.error(f"Database fix failed: {e}")

    # Fix compatibility graph
    graph_path = Path(__file__).parent / "compatibility_graph_scored.json"
    total_fixed += fix_compatibility_graph(str(graph_path))

    # Fix product metadata if exists
    metadata_path = Path(__file__).parent / "product_metadata.json"
    total_fixed += fix_json_file(str(metadata_path))

    log.info("=" * 60)
    log.info(f"TOTAL FIXED: {total_fixed}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
