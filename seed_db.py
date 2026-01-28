"""
Database seeding script for local Docker development.
Creates tables and populates from compatibility_graph_scored.json
"""
import os
import json
import asyncio
import asyncpg

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/outfit_db')
GRAPH_JSON_PATH = 'compatibility_graph_scored.json'
PRODUCTS_JSON_PATH = 'products_seed.json'


async def seed():
    print("=" * 50)
    print("SEEDING DATABASE")
    print("=" * 50)

    # Wait for database to be ready
    retries = 10
    conn = None
    for i in range(retries):
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            break
        except Exception as e:
            print(f"Waiting for database... ({i+1}/{retries})")
            await asyncio.sleep(2)

    if not conn:
        print("Failed to connect to database")
        return

    # Check if already seeded
    exists = await conn.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'compatibility_edges'
        )
    """)

    if exists:
        count = await conn.fetchval("SELECT COUNT(*) FROM compatibility_edges")
        if count > 0:
            print(f"Database already seeded ({count} edges). Skipping.")
            await conn.close()
            return

    print("\n[1/4] Creating products table...")
    await conn.execute("DROP TABLE IF EXISTS compatibility_edges CASCADE")
    await conn.execute("DROP TABLE IF EXISTS products CASCADE")

    await conn.execute("""
        CREATE TABLE products (
            sku_id TEXT PRIMARY KEY,
            image_url TEXT,
            title TEXT,
            brand TEXT,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            sub_category TEXT,
            primary_color TEXT,
            secondary_colors TEXT[],
            pattern TEXT,
            material_appearance TEXT,
            fit TEXT,
            gender TEXT NOT NULL,
            design_elements TEXT[],
            formality_level TEXT,
            versatility TEXT,
            statement_piece BOOLEAN DEFAULT FALSE,
            functional_slot TEXT NOT NULL,
            style TEXT,
            fashion_aesthetics TEXT[],
            occasion TEXT[],
            formality_score INTEGER NOT NULL,
            season TEXT[],
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    print("[2/4] Creating compatibility_edges table...")
    await conn.execute("""
        CREATE TABLE compatibility_edges (
            id SERIAL,
            sku_1 TEXT NOT NULL REFERENCES products(sku_id),
            sku_2 TEXT NOT NULL REFERENCES products(sku_id),
            target_slot TEXT NOT NULL,
            score REAL NOT NULL,
            sort_order INTEGER NOT NULL,
            PRIMARY KEY (sku_1, sku_2)
        )
    """)

    print("[3/4] Loading JSON and inserting data...")

    # Load products
    with open(PRODUCTS_JSON_PATH, 'r') as f:
        products = json.load(f)
    print(f"  Loaded {len(products)} products from {PRODUCTS_JSON_PATH}")

    # Insert products with full data
    for p in products:
        await conn.execute("""
            INSERT INTO products (
                sku_id, image_url, title, brand, type, category, sub_category,
                primary_color, secondary_colors, pattern, material_appearance,
                fit, gender, design_elements, formality_level, versatility,
                statement_piece, functional_slot, style, fashion_aesthetics,
                occasion, formality_score, season
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                $15, $16, $17, $18, $19, $20, $21, $22, $23
            ) ON CONFLICT (sku_id) DO NOTHING
        """,
            p['sku_id'], p.get('image_url'), p.get('title'), p.get('brand'),
            p['type'], p['category'], p.get('sub_category'),
            p.get('primary_color'), p.get('secondary_colors'), p.get('pattern'),
            p.get('material_appearance'), p.get('fit'), p['gender'],
            p.get('design_elements'), p.get('formality_level'), p.get('versatility'),
            p.get('statement_piece'), p['functional_slot'], p.get('style'),
            p.get('fashion_aesthetics'), p.get('occasion'), p['formality_score'],
            p.get('season')
        )

    print(f"  Inserted {len(products)} products")

    # Load compatibility graph
    with open(GRAPH_JSON_PATH, 'r') as f:
        data = json.load(f)
    graph = data['graph']

    # Insert compatibility edges
    edges = []
    for sku_1, slots in graph.items():
        for slot_name, items in slots.items():
            for sort_order, item in enumerate(items):
                edges.append((sku_1, item['sku'], slot_name.lower(), item['score'], sort_order))

    print(f"  Inserting {len(edges)} edges...")

    batch_size = 5000
    for i in range(0, len(edges), batch_size):
        batch = edges[i:i + batch_size]
        await conn.executemany("""
            INSERT INTO compatibility_edges (sku_1, sku_2, target_slot, score, sort_order)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (sku_1, sku_2) DO NOTHING
        """, batch)
        print(f"    {min(i + batch_size, len(edges))}/{len(edges)}")

    print("\n[4/4] Creating indexes...")
    await conn.execute("""
        CREATE INDEX idx_compat_sku1_slot_order
        ON compatibility_edges(sku_1, target_slot, sort_order)
    """)
    await conn.execute("""
        CREATE INDEX idx_compat_sku1_score
        ON compatibility_edges(sku_1, score DESC)
    """)
    await conn.execute("""
        CREATE INDEX idx_compat_sku2
        ON compatibility_edges(sku_2)
    """)

    final_count = await conn.fetchval("SELECT COUNT(*) FROM compatibility_edges")
    await conn.close()

    print("\n" + "=" * 50)
    print(f"SEEDING COMPLETE: {final_count} edges")
    print("=" * 50)


if __name__ == '__main__':
    asyncio.run(seed())
