"""
Database-backed Compatibility Graph Service
============================================

Uses PostgreSQL for storage with intelligent caching and batched queries.
Designed to avoid N+1 query problems by fetching data upfront.
"""

from typing import Optional
from functools import lru_cache
from cachetools import TTLCache

from app.database import get_db


class CompatibilityGraph:
    """
    Compatibility graph backed by PostgreSQL database.

    Key design principles:
    - Batch queries: fetch all needed data in single queries
    - TTL caching: cache frequently accessed data
    - Pass data through: methods return data for callers to use
    """

    _instance: Optional["CompatibilityGraph"] = None

    # TTL caches for frequently accessed data
    _compatible_cache: TTLCache  # sku -> {slot -> [items]}
    _pair_score_cache: TTLCache  # (sku1, sku2) -> score

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Initialize caches
            cls._instance._compatible_cache = TTLCache(maxsize=500, ttl=300)  # 5 min
            cls._instance._pair_score_cache = TTLCache(maxsize=50000, ttl=300)  # 5 min
            cls._instance._initialized = False
        return cls._instance

    async def initialize(self):
        """Initialize the service (verify database connection)."""
        if self._initialized:
            return

        pool = await get_db()
        async with pool.acquire() as conn:
            # Verify table exists and get count
            count = await conn.fetchval("SELECT COUNT(*) FROM compatibility_edges")
            print(f"  Compatibility edges table: {count:,} rows")

        self._initialized = True

    async def get_compatible_items(
        self,
        sku_id: str,
        slot: Optional[str] = None,
        limit: int = 50,
        min_score: float = 0.0,
    ) -> dict[str, list[dict]]:
        """
        Get compatible items for a given SKU, optionally filtered by slot.

        Returns: {slot_name: [{"sku": str, "score": float}, ...]}
        """
        # Check cache first
        cache_key = sku_id
        if cache_key in self._compatible_cache and slot is None and min_score == 0.0:
            cached = self._compatible_cache[cache_key]
            # Apply limit
            return {s: items[:limit] for s, items in cached.items()}

        pool = await get_db()

        # Build query
        if slot:
            query = """
                SELECT sku_2, target_slot, score
                FROM compatibility_edges
                WHERE sku_1 = $1 AND LOWER(target_slot) = LOWER($2) AND score >= $3
                ORDER BY score DESC, sku_2
                LIMIT $4
            """
            params = [sku_id, slot, min_score, limit]
        else:
            query = """
                SELECT sku_2, target_slot, score
                FROM compatibility_edges
                WHERE sku_1 = $1 AND score >= $2
                ORDER BY LOWER(target_slot), score DESC, sku_2
            """
            params = [sku_id, min_score]

        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        # Group by slot
        result: dict[str, list[dict]] = {}
        for row in rows:
            slot_name = row["target_slot"].lower().strip()
            if slot_name not in result:
                result[slot_name] = []
            result[slot_name].append({
                "sku": row["sku_2"],
                "score": float(row["score"]),
            })

        # Apply limit per slot
        for slot_name in result:
            result[slot_name] = result[slot_name][:limit]

        # Cache full result if no filters
        if slot is None and min_score == 0.0:
            self._compatible_cache[cache_key] = result

        return result

    async def get_all_compatible(self, sku_id: str) -> dict[str, list[dict]]:
        """
        Get ALL compatible items for a SKU (no limit, used for look generation).
        Results are cached for 5 minutes.

        Returns: {slot_name: [{"sku": str, "score": float}, ...]}
        """
        # Check cache
        if sku_id in self._compatible_cache:
            return self._compatible_cache[sku_id]

        pool = await get_db()

        query = """
            SELECT sku_2, target_slot, score
            FROM compatibility_edges
            WHERE sku_1 = $1
            ORDER BY LOWER(target_slot), score DESC, sku_2
        """

        async with pool.acquire() as conn:
            rows = await conn.fetch(query, sku_id)

        # Group by normalized slot
        result: dict[str, list[dict]] = {}
        for row in rows:
            slot_name = row["target_slot"].lower().strip()
            if slot_name not in result:
                result[slot_name] = []
            result[slot_name].append({
                "sku": row["sku_2"],
                "score": float(row["score"]),
            })

        # Cache result
        self._compatible_cache[sku_id] = result

        # Also populate pair score cache for these items
        for slot_items in result.values():
            for item in slot_items:
                key = (sku_id, item["sku"])
                self._pair_score_cache[key] = item["score"]
                # Store reverse too
                self._pair_score_cache[(item["sku"], sku_id)] = item["score"]

        return result

    async def get_compatible_with_cross_scores(
        self,
        sku_id: str,
        candidates_per_slot: int = 25
    ) -> tuple[dict[str, list[dict]], dict[tuple[str, str], float]]:
        """
        Get compatible items AND cross-scores in a SINGLE database query.

        Uses a CTE to:
        1. Find all items compatible with the base SKU
        2. Find all pairwise scores between those candidates

        Returns:
            - compatible_by_slot: {slot_name: [{"sku": str, "score": float}, ...]}
            - pair_scores: {(sku1, sku2): score} - includes base->item AND item->item scores
        """
        # Check cache - use a special marker to track if cross-scores have been fetched
        cross_scores_cache_key = f"_cross_scores_fetched_{sku_id}_{candidates_per_slot}"

        if sku_id in self._compatible_cache and cross_scores_cache_key in self._compatible_cache:
            compatible_by_slot = self._compatible_cache[sku_id]
            # Limit to candidates_per_slot
            limited = {slot: items[:candidates_per_slot] for slot, items in compatible_by_slot.items()}

            # Rebuild pair_scores from pair_score_cache
            pair_scores: dict[tuple[str, str], float] = {}
            for items in limited.values():
                for item in items:
                    # Add base->item score
                    pair_scores[(sku_id, item["sku"])] = item["score"]
                    pair_scores[(item["sku"], sku_id)] = item["score"]

            # Get cross-scores from cache (only pairs that exist)
            for key, score in self._pair_score_cache.items():
                pair_scores[key] = score

            return limited, pair_scores

        pool = await get_db()

        # Single query with CTE - fetches everything in one network round-trip
        query = """
            WITH candidates AS (
                -- Get top N candidates per slot for the base SKU
                SELECT sku_2, target_slot, score,
                       ROW_NUMBER() OVER (PARTITION BY LOWER(target_slot) ORDER BY score DESC, sku_2) as rn
                FROM compatibility_edges
                WHERE sku_1 = $1
            ),
            limited_candidates AS (
                SELECT sku_2, target_slot, score
                FROM candidates
                WHERE rn <= $2
            ),
            cross_scores AS (
                -- Get all pairwise scores between candidates
                SELECT e.sku_1, e.sku_2, e.score
                FROM compatibility_edges e
                WHERE e.sku_1 IN (SELECT sku_2 FROM limited_candidates)
                  AND e.sku_2 IN (SELECT sku_2 FROM limited_candidates)
            )
            -- Return both result sets combined with a type indicator
            SELECT 'compatible' as result_type, sku_2 as sku_a, target_slot, score, NULL as sku_b
            FROM limited_candidates
            UNION ALL
            SELECT 'cross' as result_type, sku_1 as sku_a, NULL as target_slot, score, sku_2 as sku_b
            FROM cross_scores
        """

        async with pool.acquire() as conn:
            rows = await conn.fetch(query, sku_id, candidates_per_slot)

        # Parse results
        compatible_by_slot: dict[str, list[dict]] = {}
        pair_scores: dict[tuple[str, str], float] = {}

        for row in rows:
            if row["result_type"] == "compatible":
                # Compatible item result
                slot_name = row["target_slot"].lower().strip()
                if slot_name not in compatible_by_slot:
                    compatible_by_slot[slot_name] = []
                compatible_by_slot[slot_name].append({
                    "sku": row["sku_a"],
                    "score": float(row["score"]),
                })
                # Add base->item score
                pair_scores[(sku_id, row["sku_a"])] = float(row["score"])
                pair_scores[(row["sku_a"], sku_id)] = float(row["score"])
            else:
                # Cross-score result
                sku1, sku2 = row["sku_a"], row["sku_b"]
                score = float(row["score"])
                pair_scores[(sku1, sku2)] = score
                pair_scores[(sku2, sku1)] = score

        # Sort each slot by score descending (UNION ALL may not preserve order)
        for slot_name in compatible_by_slot:
            compatible_by_slot[slot_name].sort(key=lambda x: (-x["score"], x["sku"]))

        # Cache the compatible items
        self._compatible_cache[sku_id] = compatible_by_slot

        # Cache pair scores
        for (s1, s2), score in pair_scores.items():
            self._pair_score_cache[(s1, s2)] = score

        # Mark that cross-scores have been fetched for this SKU/limit combo
        cross_scores_cache_key = f"_cross_scores_fetched_{sku_id}_{candidates_per_slot}"
        self._compatible_cache[cross_scores_cache_key] = True

        return compatible_by_slot, pair_scores

    async def get_pair_score(self, sku1: str, sku2: str) -> Optional[float]:
        """Get the compatibility score between two SKUs."""
        # Check cache (both directions)
        if (sku1, sku2) in self._pair_score_cache:
            return self._pair_score_cache[(sku1, sku2)]
        if (sku2, sku1) in self._pair_score_cache:
            return self._pair_score_cache[(sku2, sku1)]

        pool = await get_db()

        async with pool.acquire() as conn:
            # Check both directions
            score = await conn.fetchval(
                "SELECT score FROM compatibility_edges WHERE sku_1 = $1 AND sku_2 = $2",
                sku1, sku2
            )
            if score is None:
                score = await conn.fetchval(
                    "SELECT score FROM compatibility_edges WHERE sku_1 = $1 AND sku_2 = $2",
                    sku2, sku1
                )

        # Cache result
        if score is not None:
            self._pair_score_cache[(sku1, sku2)] = float(score)
            self._pair_score_cache[(sku2, sku1)] = float(score)
            return float(score)

        return None

    async def get_pair_scores_batch(
        self,
        sku1: str,
        sku2_list: list[str]
    ) -> dict[str, float]:
        """
        Get compatibility scores for sku1 paired with multiple sku2s.
        This is the KEY method for avoiding N+1 queries.

        Returns: {sku2: score}
        """
        if not sku2_list:
            return {}

        result = {}
        uncached = []

        # Check cache first
        for sku2 in sku2_list:
            if (sku1, sku2) in self._pair_score_cache:
                result[sku2] = self._pair_score_cache[(sku1, sku2)]
            elif (sku2, sku1) in self._pair_score_cache:
                result[sku2] = self._pair_score_cache[(sku2, sku1)]
            else:
                uncached.append(sku2)

        # Fetch uncached in single query
        if uncached:
            pool = await get_db()

            async with pool.acquire() as conn:
                # Check sku1 -> sku2 direction
                rows = await conn.fetch(
                    """
                    SELECT sku_2, score FROM compatibility_edges
                    WHERE sku_1 = $1 AND sku_2 = ANY($2)
                    """,
                    sku1, uncached
                )

                for row in rows:
                    sku2 = row["sku_2"]
                    score = float(row["score"])
                    result[sku2] = score
                    self._pair_score_cache[(sku1, sku2)] = score
                    self._pair_score_cache[(sku2, sku1)] = score

                # Check reverse direction for any still missing
                still_missing = [s for s in uncached if s not in result]
                if still_missing:
                    rows = await conn.fetch(
                        """
                        SELECT sku_1, score FROM compatibility_edges
                        WHERE sku_2 = $1 AND sku_1 = ANY($2)
                        """,
                        sku1, still_missing
                    )

                    for row in rows:
                        sku2 = row["sku_1"]
                        score = float(row["score"])
                        result[sku2] = score
                        self._pair_score_cache[(sku1, sku2)] = score
                        self._pair_score_cache[(sku2, sku1)] = score

        return result

    async def calculate_outfit_score(self, sku_ids: list[str]) -> dict:
        """
        Calculate total outfit score for a list of SKUs.

        Optimized: Single query fetches all pair scores at once.
        """
        if len(sku_ids) < 2:
            return {
                "total_score": 0.0,
                "pair_scores": {},
                "average_score": 0.0,
                "pair_count": 0,
            }

        # Single query: get all edges where both endpoints are in our outfit
        pool = await get_db()

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT sku_1, sku_2, score
                FROM compatibility_edges
                WHERE sku_1 = ANY($1) AND sku_2 = ANY($1)
                """,
                sku_ids
            )

        # Build a set of SKUs for O(1) lookup and track which pairs we've seen
        sku_set = set(sku_ids)
        seen_pairs = set()
        pair_scores = {}
        total_score = 0.0

        for row in rows:
            sku1, sku2 = row["sku_1"], row["sku_2"]

            # Normalize pair order to avoid counting both directions
            pair = (min(sku1, sku2), max(sku1, sku2))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            score = float(row["score"])
            pair_key = f"{sku1}:{sku2}"
            pair_scores[pair_key] = score
            total_score += score

            # Cache for future lookups
            self._pair_score_cache[(sku1, sku2)] = score
            self._pair_score_cache[(sku2, sku1)] = score

        pair_count = len(pair_scores)
        avg_score = total_score / pair_count if pair_count > 0 else 0.0

        return {
            "total_score": total_score,
            "pair_scores": pair_scores,
            "average_score": round(avg_score, 3),
            "pair_count": pair_count,
        }

    async def get_stats(self) -> dict:
        """Get graph statistics from database."""
        pool = await get_db()

        async with pool.acquire() as conn:
            total_edges = await conn.fetchval("SELECT COUNT(*) FROM compatibility_edges")
            unique_products = await conn.fetchval(
                "SELECT COUNT(DISTINCT sku_1) FROM compatibility_edges"
            )
            avg_score = await conn.fetchval(
                "SELECT AVG(score) FROM compatibility_edges"
            )

        return {
            "total_edges": total_edges,
            "unique_products": unique_products,
            "average_score": round(float(avg_score), 3) if avg_score else 0,
        }

    def clear_cache(self):
        """Clear all caches (useful for testing or after data updates)."""
        self._compatible_cache.clear()
        self._pair_score_cache.clear()


# Singleton accessor
_graph_instance: Optional[CompatibilityGraph] = None


async def get_compatibility_graph() -> CompatibilityGraph:
    """Get the singleton compatibility graph service."""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = CompatibilityGraph()
        await _graph_instance.initialize()
    return _graph_instance
