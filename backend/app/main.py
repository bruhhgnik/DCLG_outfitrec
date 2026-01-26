from contextlib import asynccontextmanager
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Database
from app.services.compatibility import get_compatibility_graph
from app.services.look_generator import get_look_generator
from app.services.product import _get_cached_products
from app.routers import products, outfits, stats

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start = time.time()

    print("Connecting to database...")
    await Database.connect()

    print("Pre-warming product cache...")
    cache = await _get_cached_products()
    print(f"  Cached {len(cache)} products")

    print("Loading compatibility graph...")
    get_compatibility_graph()

    print("Loading look generator with optimized indexes...")
    lg = get_look_generator()
    print(f"  Pair index: {len(lg._pair_index):,} entries")

    print(f"Startup complete in {time.time() - start:.2f}s!")

    yield

    # Shutdown
    print("Shutting down...")
    await Database.disconnect()


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="AI-powered outfit compatibility and recommendation API",
    lifespan=lifespan,
)

# CORS - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(products.router, prefix="/api/v1")
app.include_router(outfits.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/api/v1/stats/health",
    }
