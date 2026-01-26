# DCLG Outfit Recommender

A fashion recommendation system that generates complete outfit looks from any starting piece. Built this to solve the problem of "what goes with this?" using a pre-computed compatibility graph and dimension-based clustering.

## What it does

Pick a product (say, a black hoodie) and the system generates multiple outfit combinations - not just "here's stuff that matches" but actual coherent looks like "Street Style" or "Monochrome Flow". Each look is independently valid, not ranked against each other.

## How it works

Instead of computing compatibility on every request (slow), I pre-computed a graph of 264K+ product pairs with scores based on color, style, formality, occasion, etc. At runtime, it's just hash lookups - ~200ms response time.

The algorithm clusters compatible items by "dimensions" (occasion, aesthetic, color strategy) and builds looks that are internally coherent within each dimension.

## Stack

- **Backend**: FastAPI + Python
- **Frontend**: Next.js + Tailwind
- **Database**: Supabase (Postgres)
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

You'll need the data files (`product_metadata.json` and `compatibility_graph_scored.json`) - these aren't in the repo because they're large. Check releases or generate them using the scripts in `/scripts`.

## API

```
POST /api/v1/outfits/generate-looks?base_sku=XXX&num_looks=3
GET  /api/v1/products
GET  /api/v1/products/{sku}
GET  /api/v1/stats/health
```

## The algorithm (DCLG)

Documented in `/docs/algorithm.md` but basically:

1. Get all compatible items for the base product (from pre-computed graph)
2. Filter by validity rules (formality gap ≤1, occasion overlap, season match)
3. Cluster remaining items by dimension (aesthetic, occasion, color)
4. For each look, pick the best item per slot that maximizes coherence with items already in the look
5. Apply fashion rules (no statement top + closed outerwear, color harmony for accessories, etc.)

## Project structure

```
├── backend/          # FastAPI server
│   └── app/
│       └── services/
│           └── look_generator.py   # the main algorithm
├── client/           # Next.js frontend
├── scripts/          # data processing utilities
└── database/         # SQL schema
```

## License

MIT
