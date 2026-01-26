"""
Product Metadata Ingestion Script
=================================
Loads product_metadata.json and inserts into Supabase PostgreSQL.

Features:
- Batch insert using execute_values
- ON CONFLICT DO NOTHING for idempotency
- Text normalization (lowercase, strip whitespace)
- Safe type coercion
- Detailed logging
"""

import json
import os
import sys
import logging
from pathlib import Path
from typing import Any, Optional, List

import psycopg2
from psycopg2.extras import execute_values

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # dotenv not installed, use system env vars

# -----------------------------------------------------------------------------
# LOGGING SETUP
# -----------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# DATABASE CONFIG (from environment variables)
# -----------------------------------------------------------------------------

DB_HOST = os.getenv("SUPABASE_DB_HOST", "localhost")
DB_PORT = os.getenv("SUPABASE_DB_PORT", "5432")
DB_NAME = os.getenv("SUPABASE_DB_NAME", "postgres")
DB_USER = os.getenv("SUPABASE_DB_USER", "postgres")
DB_PASS = os.getenv("SUPABASE_DB_PASSWORD", "")

# -----------------------------------------------------------------------------
# NORMALIZATION FUNCTIONS
# -----------------------------------------------------------------------------

def normalize_str(value: Any) -> Optional[str]:
    """
    Normalize a string value: strip whitespace, convert to lowercase.
    Returns None if value is None or empty after stripping.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    value = value.strip().lower()
    return value if value else None


def normalize_list(value: Any) -> List[str]:
    """
    Normalize a list of strings.
    - If None, return empty list
    - If string, wrap in list
    - Normalize each element (strip, lowercase)
    """
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if item is not None:
            normalized = str(item).strip().lower()
            if normalized:
                result.append(normalized)
    return result


def safe_bool(value: Any) -> bool:
    """Safely convert value to boolean."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value)


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to integer."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

# -----------------------------------------------------------------------------
# ROW EXTRACTION
# -----------------------------------------------------------------------------

def extract_row(product: dict) -> tuple:
    """
    Extract a single row tuple from product dict.
    Applies normalization to all text fields.
    Handles missing keys gracefully.
    """
    vf = product.get("visual_features") or {}

    return (
        # sku_id - NOT NULL, keep original case for ID
        product.get("sku_id"),
        # image_url - NOT NULL, keep original (check both image_url and image_file for backwards compat)
        product.get("image_url") or product.get("image_file"),
        # title - normalized
        normalize_str(product.get("title")),
        # brand - normalized
        normalize_str(product.get("brand")),
        # type - NOT NULL, normalized
        normalize_str(vf.get("type")),
        # category - NOT NULL, normalized
        normalize_str(vf.get("category")),
        # sub_category - normalized
        normalize_str(vf.get("sub_category")),
        # primary_color - normalized
        normalize_str(vf.get("primary_color")),
        # secondary_colors - normalized list
        normalize_list(vf.get("secondary_colors")),
        # pattern - normalized
        normalize_str(vf.get("pattern")),
        # material_appearance - normalized
        normalize_str(vf.get("material_appearance")),
        # fit - normalized
        normalize_str(vf.get("fit")),
        # gender - NOT NULL, normalized
        normalize_str(vf.get("gender")),
        # design_elements - normalized list
        normalize_list(vf.get("design_elements")),
        # formality_level - normalized
        normalize_str(vf.get("formality_level")),
        # versatility - normalized
        normalize_str(vf.get("versatility")),
        # statement_piece - boolean
        safe_bool(vf.get("statement_piece")),
        # functional_slot - NOT NULL, normalized
        normalize_str(vf.get("functional_slot")),
        # style - VARCHAR, normalized string
        normalize_str(vf.get("style")),
        # fashion_aesthetics - normalized list
        normalize_list(vf.get("fashion_aesthetics")),
        # occasion - normalized list
        normalize_list(vf.get("occasion")),
        # formality_score - NOT NULL, integer
        safe_int(vf.get("formality_score"), default=1),
        # season - normalized list
        normalize_list(vf.get("season")),
    )

# -----------------------------------------------------------------------------
# VALIDATION
# -----------------------------------------------------------------------------

def validate_row(row: tuple, sku_id: str) -> Optional[str]:
    """
    Validate that NOT NULL fields are present.
    Returns error message if invalid, None if valid.
    """
    # Indices of NOT NULL fields
    # 0: sku_id, 1: image_file, 4: type, 5: category, 12: gender, 17: functional_slot, 21: formality_score
    if not row[0]:
        return "missing sku_id"
    if not row[1]:
        return "missing image_url"
    if not row[4]:
        return "missing type"
    if not row[5]:
        return "missing category"
    if not row[12]:
        return "missing gender"
    if not row[17]:
        return "missing functional_slot"
    # formality_score has default so always valid
    return None

# -----------------------------------------------------------------------------
# DATABASE OPERATIONS
# -----------------------------------------------------------------------------

def get_connection():
    """Create database connection."""
    log.info(f"Connecting to {DB_HOST}:{DB_PORT}/{DB_NAME}")
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )


def insert_batch(conn, rows: List[tuple]) -> int:
    """
    Insert rows using execute_values with ON CONFLICT DO NOTHING.
    Returns number of rows actually inserted.
    """
    sql = """
        INSERT INTO products (
            sku_id,
            image_url,
            title,
            brand,
            type,
            category,
            sub_category,
            primary_color,
            secondary_colors,
            pattern,
            material_appearance,
            fit,
            gender,
            design_elements,
            formality_level,
            versatility,
            statement_piece,
            functional_slot,
            style,
            fashion_aesthetics,
            occasion,
            formality_score,
            season
        ) VALUES %s
        ON CONFLICT (sku_id) DO NOTHING
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=100)
        inserted = cur.rowcount
        conn.commit()
    return inserted

# -----------------------------------------------------------------------------
# MAIN INGESTION LOGIC
# -----------------------------------------------------------------------------

def load_json(filepath: str) -> List[dict]:
    """Load products from JSON file."""
    log.info(f"Loading JSON from: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    products = data.get("products", [])
    log.info(f"Records read from JSON: {len(products)}")
    return products


def ingest(json_path: str):
    """Main ingestion function."""
    # Load data
    products = load_json(json_path)
    if not products:
        log.error("No products found in JSON file")
        return

    # Process rows
    valid_rows = []
    skipped = []
    failures = []

    for idx, product in enumerate(products):
        sku = product.get("sku_id", f"row_{idx}")
        try:
            row = extract_row(product)
            error = validate_row(row, sku)
            if error:
                skipped.append((sku, error))
                log.warning(f"Skipped {sku}: {error}")
            else:
                valid_rows.append(row)
        except Exception as e:
            failures.append((sku, str(e)))
            log.error(f"Failed to process {sku}: {e}")

    log.info(f"Valid rows prepared: {len(valid_rows)}")
    log.info(f"Skipped (validation): {len(skipped)}")
    log.info(f"Failures (exceptions): {len(failures)}")

    if not valid_rows:
        log.error("No valid rows to insert")
        return

    # Insert into database
    conn = None
    inserted = 0
    try:
        conn = get_connection()
        log.info("Connected to database")
        inserted = insert_batch(conn, valid_rows)
    except psycopg2.Error as e:
        log.error(f"Database error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

    # Final summary
    duplicates = len(valid_rows) - inserted
    log.info("=" * 60)
    log.info("INGESTION SUMMARY")
    log.info("=" * 60)
    log.info(f"  Records read from JSON:    {len(products)}")
    log.info(f"  Valid rows prepared:       {len(valid_rows)}")
    log.info(f"  Rows inserted:             {inserted}")
    log.info(f"  Duplicates skipped (DB):   {duplicates}")
    log.info(f"  Validation skipped:        {len(skipped)}")
    log.info(f"  Processing failures:       {len(failures)}")
    log.info("=" * 60)

    if skipped:
        log.info("Skipped records:")
        for sku, reason in skipped[:10]:
            log.info(f"  - {sku}: {reason}")
        if len(skipped) > 10:
            log.info(f"  ... and {len(skipped) - 10} more")

    if failures:
        log.info("Failed records:")
        for sku, reason in failures[:10]:
            log.info(f"  - {sku}: {reason}")
        if len(failures) > 10:
            log.info(f"  ... and {len(failures) - 10} more")


def main():
    json_path = os.getenv("PRODUCT_JSON_PATH", "D:/jobmaxing/product_metadata.json")

    if not os.path.exists(json_path):
        log.error(f"JSON file not found: {json_path}")
        sys.exit(1)

    ingest(json_path)


if __name__ == "__main__":
    main()
