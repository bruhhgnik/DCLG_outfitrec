# Outfit Studio

A fashion recommendation system that generates complete outfit looks from any starting piece using a compatibility graph and dimension-based clustering.

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

## License

MIT
