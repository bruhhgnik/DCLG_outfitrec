#!/usr/bin/env python3
"""
Export Compatibility Graph from Database to JSON
=================================================

Run this script to generate the compatibility_graph.json file from the database.
The JSON file is then used by the app for fast in-memory lookups.

Usage:
    python export_graph_to_json.py

The script will:
1. Connect to Supabase
2. Fetch all compatibility edges
3. Build the graph structure
4. Save to compatibility_graph.json
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def export_graph():
    """Export compatibility graph from database to JSON."""

    # Build connection string
    host = os.getenv("SUPABASE_DB_HOST")
    port = os.getenv("SUPABASE_DB_PORT", "5432")
    user = os.getenv("SUPABASE_DB_USER", "postgres")
    password = os.getenv("SUPABASE_DB_PASSWORD")
    database = os.getenv("SUPABASE_DB_NAME", "postgres")

    if not host or not password:
        print("Error: Missing database credentials in environment variables")
        print("Required: SUPABASE_DB_HOST, SUPABASE_DB_PASSWORD")
        sys.exit(1)

    dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"

    print("=" * 60)
    print("EXPORTING COMPATIBILITY GRAPH TO JSON")
    print("=" * 60)
    print()

    # Connect to database
    print("1. Connecting to database...")
    conn = await asyncpg.connect(dsn)

    try:
        # Get total count
        total = await conn.fetchval("SELECT COUNT(*) FROM compatibility_edges")
        print(f"   Found {total:,} compatibility edges")

        # Fetch all edges
        print("2. Fetching all edges...")
        rows = await conn.fetch("""
            SELECT sku_1, sku_2, target_slot, score
            FROM compatibility_edges
            ORDER BY sku_1, target_slot, score DESC
        """)
        print(f"   Fetched {len(rows):,} rows")

        # Build graph structure
        print("3. Building graph structure...")
        graph = defaultdict(lambda: defaultdict(list))

        for row in rows:
            sku_1 = row["sku_1"]
            sku_2 = row["sku_2"]
            slot = row["target_slot"].lower()
            score = float(row["score"])

            graph[sku_1][slot].append({
                "sku": sku_2,
                "score": score
            })

        # Convert defaultdict to regular dict
        graph_dict = {
            sku: dict(slots)
            for sku, slots in graph.items()
        }

        print(f"   Built graph for {len(graph_dict):,} products")

        # Calculate metadata
        print("4. Calculating metadata...")
        total_edges = sum(
            len(items)
            for slots in graph_dict.values()
            for items in slots.values()
        )

        all_scores = [
            item["score"]
            for slots in graph_dict.values()
            for items in slots.values()
            for item in items
        ]
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0

        metadata = {
            "total_edges": total_edges,
            "unique_products": len(graph_dict),
            "average_score": round(avg_score, 3),
            "exported_at": datetime.now().isoformat(),
        }

        print(f"   Total edges: {total_edges:,}")
        print(f"   Unique products: {len(graph_dict):,}")
        print(f"   Average score: {avg_score:.3f}")

        # Save to JSON
        output_path = Path(__file__).parent / "compatibility_graph.json"
        print(f"5. Saving to {output_path}...")

        output = {
            "metadata": metadata,
            "graph": graph_dict
        }

        with open(output_path, "w") as f:
            json.dump(output, f, separators=(",", ":"))  # Compact JSON

        file_size = output_path.stat().st_size / (1024 * 1024)
        print(f"   Saved! File size: {file_size:.2f} MB")

        print()
        print("=" * 60)
        print("EXPORT COMPLETE")
        print("=" * 60)
        print()
        print(f"Graph saved to: {output_path}")
        print("Deploy this file with your backend to enable fast lookups.")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(export_graph())
