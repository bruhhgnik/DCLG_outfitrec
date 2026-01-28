# Outfit Studio

A fashion recommendation system that generates complete outfit looks from any starting piece using a compatibility graph and dimension-based clustering.

**Data Source:** Products come from the provided CSV + ~300 additional products scraped from StockX using a custom scraper I built to efficiently extract product details.

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── config.py               # Environment variables
│   │   ├── database.py             # Postgres connection pool
│   │   ├── models/
│   │   │   └── product.py          # Pydantic schemas
│   │   ├── routers/
│   │   │   ├── products.py         # /products endpoints
│   │   │   ├── outfits.py          # /outfits endpoints (generate-looks)
│   │   │   └── stats.py            # /stats endpoints (health check)
│   │   └── services/
│   │       ├── product.py          # Product DB queries
│   │       ├── compatibility.py    # Compatibility graph queries
│   │       └── look_generator.py   # DCLG algorithm
│   └── run.py                      # Dev server launcher
├── client/
│   └── src/
│       ├── app/
│       │   ├── page.tsx            # Home page
│       │   ├── products/page.tsx   # Product listing
│       │   └── product/[sku]/      # Product detail + looks
│       ├── components/
│       │   ├── LooksSection.tsx    # Renders generated outfits
│       │   ├── ProductCard.tsx     # Product thumbnail
│       │   └── FilterSidebar.tsx   # Category/brand filters
│       └── lib/
│           └── api.ts              # API client
├── docker-compose.yml              # Local dev setup
├── Dockerfile                      # Backend container
├── seed_db.py                      # Seeds Postgres with products + edges
└── compatibility_graph_scored.json # Pre-computed compatibility data
```

---

## Local Setup

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [Node.js](https://nodejs.org/) v18+

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/bruhhgnik/DCLG_outfitrec.git
   cd DCLG_outfitrec
   ```

2. **Start the backend**
   ```bash
   docker compose up --build
   ```
   Wait until you see: `Uvicorn running on http://0.0.0.0:8000`

3. **Start the frontend** (new terminal)
   ```bash
   cd client
   npm install
   npm run dev
   ```

4. **Open the app** at [http://localhost:3000](http://localhost:3000)

### Stopping

```bash
docker compose down
```

---

## Overview

Pick any product and the system generates multiple outfit combinations - not just "items that match" but coherent looks like "Street Style" or "Monochrome Flow".

## How It Works

### The Compatibility Graph

I pre-computed compatibility scores (0-1) for every product pair and stored them in Postgres. ~400K edges for 692 products. Scores account for color harmony, style alignment, occasion, and season.

### The Algorithm (DCLG)

When you pick a product:

1. Pull all compatible items from the graph (single query)
2. Filter out bad pairs - formality gaps, season mismatches, silhouette conflicts (no knitwear under hoodies, no statement tops with athleisure bottoms, etc.)
3. Cluster what's left by dimension - occasion (casual, gym, date), aesthetic (streetwear, minimalist), or color strategy (monochrome, neutral, accent)
4. For each cluster, greedily pick the best item per slot that fits with what's already in the look
5. Make sure every look has footwear and an accessory

### Why it's fast

Everything is precomputed. The API just does one indexed DB query, filters in memory, and returns. Response time is 50-80ms.

### Stack

- **Backend**: FastAPI + PostgreSQL
- **Frontend**: Next.js 14 + TanStack Query
- **Hosting**: Railway

### API

```
GET /api/v1/outfits/generate-looks?base_sku=XXX&num_looks=10
GET /api/v1/products
GET /api/v1/products/{sku}
```

### Performance Challenges

**Problem 1: Memory**
- Original approach loaded a 46MB JSON file into memory on startup
- 392K edges for 800 products = ~140MB RAM
- Would scale to ~7GB at 10K products - not viable for serverless

**Solution:** Moved to PostgreSQL. Memory dropped from ~140MB to ~15MB.

**Problem 2: Cold query latency**
- First DB query after migration was ~230ms (vs <1ms with in-memory JSON)

**Solution:**
- Added indexes on `(sku_1, target_slot, sort_order)` and `(sku_1, score DESC)`
- Server-side TTL cache (5 min) - repeat queries hit cache at ~5ms
- Client-side TanStack Query cache - same user gets instant results

**Current performance:** 50-80ms response time for generate-looks.

## License

MIT
