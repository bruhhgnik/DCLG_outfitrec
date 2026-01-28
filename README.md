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

### How it works

1. Pre-computed compatibility scores between all product pairs stored in PostgreSQL
2. Algorithm clusters compatible items by dimensions (occasion, aesthetic, color)
3. Builds looks that are internally coherent within each dimension

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
