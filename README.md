# Outfit Studio

A fashion recommendation system that generates complete outfit looks from any starting piece. Built to solve the "what goes with this?" problem using a database-backed compatibility graph and dimension-based clustering.

## What it does

Pick a product (say, a black hoodie) and the system generates multiple outfit combinations - not just "here's stuff that matches" but actual coherent looks like "Street Style" or "Monochrome Flow". Each look is independently valid, not ranked against each other.

## How it works

The algorithm clusters compatible items by "dimensions" (occasion, aesthetic, color strategy) and builds looks that are internally coherent within each dimension.

### Performance Architecture

We went through several iterations to get this fast and scalable:

**The Problem**: Originally loaded a 46MB JSON file with 392K+ compatibility edges into memory on startup. This worked fine for 800 products, but would balloon to ~7GB at 10K products - not viable for serverless deployments.

**The Solution**: Migrated the compatibility graph to PostgreSQL (Supabase) with proper indexing.

| Approach | Memory Usage | Startup Time | Query Time |
|----------|-------------|--------------|------------|
| JSON in memory | ~140MB | 3-4 seconds | <1ms |
| PostgreSQL + caching | ~15MB | <1 second | 5ms (warm) / 230ms (cold) |

The tradeoff: slightly slower cold queries, but 9x less memory and linear scaling with products.

### Caching Strategy

We use a two-layer caching approach:

1. **Server-side TTL cache** (5 minutes): Caches compatibility lookups in memory. After the first user requests looks for a product, subsequent requests are ~5ms.

2. **Client-side TanStack Query**: Caches API responses in the browser. Same user revisiting a product gets instant results (0ms network).

This means:
- First visitor to a product: ~230ms (database query)
- Second visitor to same product: ~5ms (server cache hit)
- Same visitor returning: instant (browser cache hit)

## Stack

- **Backend**: FastAPI + Python + asyncpg
- **Frontend**: Next.js 14 + TanStack Query + Tailwind
- **Database**: Supabase (PostgreSQL)
- **Hosting**: Render (backend) + Vercel (frontend)

## Running locally

Backend:
```bash
cd backend
pip install -r requirements.txt
python run.py
```

Frontend:
```bash
cd client
npm install
npm run dev
```

You'll need a `.env` file in the backend folder with your Supabase credentials:
```
SUPABASE_DB_HOST=your-project.supabase.co
SUPABASE_DB_PASSWORD=your-password
```

## Database Schema

The compatibility data lives in two tables:

```sql
-- Products table
CREATE TABLE products (
    sku_id VARCHAR PRIMARY KEY,
    title VARCHAR,
    brand VARCHAR,
    type VARCHAR,
    functional_slot VARCHAR,  -- base top, outerwear, footwear, etc.
    primary_color VARCHAR,
    -- ... other metadata
);

-- Pre-computed compatibility scores
CREATE TABLE compatibility_edges (
    sku_1 VARCHAR NOT NULL,
    sku_2 VARCHAR NOT NULL,
    target_slot VARCHAR NOT NULL,
    score FLOAT NOT NULL,
    PRIMARY KEY (sku_1, sku_2)
);

-- Index for fast lookups
CREATE INDEX idx_compat_sku1_slot_score
ON compatibility_edges(sku_1, target_slot, score DESC);
```

## API

```
POST /api/v1/outfits/generate-looks?base_sku=XXX&num_looks=10
GET  /api/v1/products
GET  /api/v1/products/{sku}
GET  /api/v1/outfits/{sku}/compatible
POST /api/v1/outfits/score
GET  /api/v1/stats/health
```

## The Algorithm (DCLG)

Dimension-Constrained Look Generation:

1. Fetch all compatible items for the base product from the database (single query)
2. Batch fetch product metadata for all compatible SKUs (single query)
3. Filter by validity rules (formality gap ≤1, occasion overlap, season match)
4. Cluster remaining items by dimension (aesthetic, occasion, color)
5. For each look, pick the best item per slot that maximizes coherence with items already selected
6. Apply fashion rules (no statement top + closed outerwear, color harmony for accessories, etc.)

Key optimization: all database queries happen upfront, then the algorithm runs entirely in-memory with O(1) hash lookups.

## Project Structure

```
├── backend/
│   └── app/
│       ├── services/
│       │   ├── compatibility.py   # DB-backed compatibility graph
│       │   ├── look_generator.py  # DCLG algorithm
│       │   └── product.py         # Product service
│       ├── routers/               # API endpoints
│       ├── models/                # Pydantic models
│       └── database.py            # Connection pooling
├── client/
│   └── src/
│       ├── providers/
│       │   └── QueryProvider.tsx  # TanStack Query setup
│       └── components/
│           ├── LooksSection.tsx   # Look generation UI
│           └── OutfitBuilder.tsx  # Product selection
└── schema.sql                     # Database schema
```

## Adding New Products

When you add a new product to the `products` table, you'll also need to generate compatibility edges for it. The compatibility scores aren't auto-generated - run the scoring script to compute edges between the new product and existing ones, then insert into `compatibility_edges`.

## License

MIT
