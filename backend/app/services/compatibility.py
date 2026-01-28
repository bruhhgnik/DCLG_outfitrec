"""
Database-based Compatibility Graph Service
==========================================

Queries compatibility_edges table with indexes for fast lookups.
Preserves same interface as JSON-based service.
Uses sort_order column to maintain consistent ordering.
"""

import logging
import time
from typing import Optional
import asyncpg

from app.database import get_db

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.INFO)


class CompatibilityGraphDB:
    """
    Compatibility graph backed by PostgreSQL with indexes.

    All lookups use indexed queries on compatibility_edges table.
    sort_order column ensures results match JSON order exactly.
    """

    _instance: Optional["CompatibilityGraphDB"] = None
    _initialized: bool = False
    _stats_cache: Optional[dict] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self):
        """Initialize the service (verify DB connection)."""
        if self._initialized:
            return

        pool = await get_db()
        async with pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM compatibility_edges")
            print(f"  DB compatibility graph initialized: {count:,} edges")

        self._initialized = True

    @property
    def graph(self) -> dict:
        """For compatibility with JSON-based service (returns empty dict)."""
        return {}

    async def get_compatible_items(
        self,
        sku_id: str,
        slot: Optional[str] = None,
        limit: int = 50,
        min_score: float = 0.0,
    ) -> dict[str, list[dict]]:
        """Get compatible items for a given SKU, optionally filtered by slot."""
        start = time.perf_counter()
        pool = await get_db()
        async with pool.acquire() as conn:
            if slot:
                slot_lower = slot.lower()
                rows = await conn.fetch("""
                    SELECT sku_2 as sku, target_slot, score
                    FROM compatibility_edges
                    WHERE sku_1 = $1 AND LOWER(target_slot) = $2 AND score >= $3
                    ORDER BY sort_order
                    LIMIT $4
                """, sku_id, slot_lower, min_score, limit)

                elapsed = (time.perf_counter() - start) * 1000
                if not rows:
                    logger.info(f"[DB QUERY] get_compatible_items({sku_id}, slot={slot}) -> 0 results in {elapsed:.2f}ms")
                    return {}

                items = [{"sku": row["sku"], "score": row["score"]} for row in rows]
                logger.info(f"[DB QUERY] get_compatible_items({sku_id}, slot={slot}) -> {len(items)} results in {elapsed:.2f}ms")
                return {slot_lower: items}

            else:
                rows = await conn.fetch("""
                    SELECT sku_2 as sku, target_slot, score
                    FROM compatibility_edges
                    WHERE sku_1 = $1 AND score >= $2
                    ORDER BY target_slot, sort_order
                """, sku_id, min_score)

                elapsed = (time.perf_counter() - start) * 1000
                if not rows:
                    logger.info(f"[DB QUERY] get_compatible_items({sku_id}, all slots) -> 0 results in {elapsed:.2f}ms")
                    return {}

                # Group by slot
                result = {}
                slot_counts = {}
                for row in rows:
                    slot_lower = row["target_slot"].lower()
                    if slot_lower not in result:
                        result[slot_lower] = []
                        slot_counts[slot_lower] = 0

                    if slot_counts[slot_lower] < limit:
                        result[slot_lower].append({
                            "sku": row["sku"],
                            "score": row["score"]
                        })
                        slot_counts[slot_lower] += 1

                total_items = sum(len(v) for v in result.values())
                logger.info(f"[DB QUERY] get_compatible_items({sku_id}, all slots) -> {total_items} results across {len(result)} slots in {elapsed:.2f}ms")
                return result

    async def get_all_compatible(self, sku_id: str) -> dict[str, list[dict]]:
        """Get ALL compatible items for a SKU (used for look generation)."""
        start = time.perf_counter()
        pool = await get_db()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT sku_2 as sku, target_slot, score
                FROM compatibility_edges
                WHERE sku_1 = $1
                ORDER BY target_slot, sort_order
            """, sku_id)

            elapsed = (time.perf_counter() - start) * 1000
            if not rows:
                logger.info(f"[DB QUERY] get_all_compatible({sku_id}) -> 0 results in {elapsed:.2f}ms")
                return {}

            # Group by slot
            result = {}
            for row in rows:
                slot_lower = row["target_slot"].lower()
                if slot_lower not in result:
                    result[slot_lower] = []
                result[slot_lower].append({
                    "sku": row["sku"],
                    "score": row["score"]
                })

            total_items = sum(len(v) for v in result.values())
            logger.info(f"[DB QUERY] get_all_compatible({sku_id}) -> {total_items} results across {len(result)} slots in {elapsed:.2f}ms")
            return result

    async def get_compatible_with_cross_scores(
        self,
        sku_id: str,
        candidates_per_slot: int = 25
    ) -> tuple[dict[str, list[dict]], dict[tuple[str, str], float]]:
        """
        Get compatible items AND cross-scores between them.

        Returns:
            - compatible_by_slot: {slot_name: [{"sku": str, "score": float}, ...]}
            - pair_scores: {(sku1, sku2): score}
        """
        start = time.perf_counter()
        pool = await get_db()
        async with pool.acquire() as conn:
            # Step 1: Get compatible items (limited per slot)
            rows = await conn.fetch("""
                SELECT sku_2 as sku, target_slot, score
                FROM compatibility_edges
                WHERE sku_1 = $1
                ORDER BY target_slot, sort_order
            """, sku_id)

            if not rows:
                return {}, {}

            # Group by slot with limit
            compatible_by_slot = {}
            slot_counts = {}
            all_candidate_skus = set()

            for row in rows:
                slot_lower = row["target_slot"].lower()
                if slot_lower not in compatible_by_slot:
                    compatible_by_slot[slot_lower] = []
                    slot_counts[slot_lower] = 0

                if slot_counts[slot_lower] < candidates_per_slot:
                    compatible_by_slot[slot_lower].append({
                        "sku": row["sku"],
                        "score": row["score"]
                    })
                    all_candidate_skus.add(row["sku"])
                    slot_counts[slot_lower] += 1

            # Step 2: Build pair scores
            pair_scores = {}

            # Base to candidate scores
            for items in compatible_by_slot.values():
                for item in items:
                    pair_scores[(sku_id, item["sku"])] = item["score"]
                    pair_scores[(item["sku"], sku_id)] = item["score"]

            # Step 3: Get cross-scores between candidates
            if all_candidate_skus:
                candidate_list = list(all_candidate_skus)
                cross_rows = await conn.fetch("""
                    SELECT sku_1, sku_2, score
                    FROM compatibility_edges
                    WHERE sku_1 = ANY($1) AND sku_2 = ANY($1)
                """, candidate_list)

                for row in cross_rows:
                    pair_scores[(row["sku_1"], row["sku_2"])] = row["score"]
                    pair_scores[(row["sku_2"], row["sku_1"])] = row["score"]

            elapsed = (time.perf_counter() - start) * 1000
            total_candidates = sum(len(v) for v in compatible_by_slot.values())
            logger.info(f"[DB QUERY] get_compatible_with_cross_scores({sku_id}) -> {total_candidates} candidates, {len(pair_scores)} pair scores in {elapsed:.2f}ms")
            return compatible_by_slot, pair_scores

    async def get_pair_score(self, sku1: str, sku2: str) -> Optional[float]:
        """Get the compatibility score between two SKUs."""
        start = time.perf_counter()
        pool = await get_db()
        async with pool.acquire() as conn:
            score = await conn.fetchval("""
                SELECT score FROM compatibility_edges
                WHERE sku_1 = $1 AND sku_2 = $2
            """, sku1, sku2)

            if score is None:
                # Try reverse
                score = await conn.fetchval("""
                    SELECT score FROM compatibility_edges
                    WHERE sku_1 = $1 AND sku_2 = $2
                """, sku2, sku1)

            elapsed = (time.perf_counter() - start) * 1000
            logger.info(f"[DB QUERY] get_pair_score({sku1}, {sku2}) -> {score} in {elapsed:.2f}ms")
            return score

    async def get_pair_scores_batch(
        self,
        sku1: str,
        sku2_list: list[str]
    ) -> dict[str, float]:
        """Get compatibility scores for sku1 paired with multiple sku2s."""
        if not sku2_list:
            return {}

        pool = await get_db()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT sku_2, score FROM compatibility_edges
                WHERE sku_1 = $1 AND sku_2 = ANY($2)
            """, sku1, sku2_list)

            return {row["sku_2"]: row["score"] for row in rows}

    async def calculate_outfit_score(self, sku_ids: list[str]) -> dict:
        """Calculate total outfit score for a list of SKUs."""
        pair_scores = {}
        total_score = 0.0
        pair_count = 0

        for i, sku1 in enumerate(sku_ids):
            for sku2 in sku_ids[i + 1:]:
                score = await self.get_pair_score(sku1, sku2)

                if score is not None:
                    pair_key = f"{sku1}:{sku2}"
                    pair_scores[pair_key] = score
                    total_score += score
                    pair_count += 1

        avg_score = total_score / pair_count if pair_count > 0 else 0.0

        return {
            "total_score": total_score,
            "pair_scores": pair_scores,
            "average_score": round(avg_score, 3),
            "pair_count": pair_count,
        }

    async def get_stats(self) -> dict:
        """Get graph statistics from database."""
        if self._stats_cache:
            logger.info(f"[DB QUERY] get_stats() -> cached: {self._stats_cache['total_edges']} edges")
            return self._stats_cache

        start = time.perf_counter()
        pool = await get_db()
        async with pool.acquire() as conn:
            total_edges = await conn.fetchval("SELECT COUNT(*) FROM compatibility_edges")
            unique_products = await conn.fetchval("SELECT COUNT(DISTINCT sku_1) FROM compatibility_edges")
            avg_score = await conn.fetchval("SELECT AVG(score) FROM compatibility_edges")

            self._stats_cache = {
                "total_edges": total_edges,
                "total_products": unique_products,
                "avg_score": round(float(avg_score or 0), 3),
            }

        elapsed = (time.perf_counter() - start) * 1000
        logger.info(f"[DB QUERY] get_stats() -> {total_edges} edges, {unique_products} products in {elapsed:.2f}ms")
        return self._stats_cache


# Singleton accessor
_graph_instance: Optional[CompatibilityGraphDB] = None


async def get_compatibility_graph() -> CompatibilityGraphDB:
    """Get the singleton compatibility graph service."""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = CompatibilityGraphDB()
        await _graph_instance.initialize()
    return _graph_instance
