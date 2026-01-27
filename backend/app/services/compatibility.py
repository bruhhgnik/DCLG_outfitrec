"""
JSON-based Compatibility Graph Service
=======================================

Loads compatibility graph from JSON file for instant in-memory lookups.
Much faster than database queries - all operations are O(1) dictionary lookups.
"""

import json
from pathlib import Path
from typing import Optional
from functools import lru_cache

from app.config import get_settings

settings = get_settings()


class CompatibilityGraph:
    """
    Compatibility graph loaded from JSON file.

    All lookups are instant in-memory dictionary operations.
    """

    _instance: Optional["CompatibilityGraph"] = None
    _graph: dict = {}
    _metadata: dict = {}
    _loaded: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, path: Optional[str] = None):
        """Load the compatibility graph from JSON file."""
        if self._loaded:
            return

        if path is None:
            path = settings.compatibility_graph_path

        graph_path = Path(path)
        if not graph_path.is_absolute():
            # Look in backend directory
            graph_path = Path(__file__).parent.parent.parent / path

        if not graph_path.exists():
            print(f"Warning: Compatibility graph not found at {graph_path}")
            self._graph = {}
            self._metadata = {}
            self._loaded = True
            return

        print(f"Loading compatibility graph from {graph_path}...")
        with open(graph_path, "r") as f:
            data = json.load(f)

        self._metadata = data.get("metadata", {})
        self._graph = data.get("graph", {})
        self._loaded = True
        print(f"  Loaded {len(self._graph)} products with compatibility data")

    @property
    def metadata(self) -> dict:
        return self._metadata

    @property
    def graph(self) -> dict:
        return self._graph

    async def get_compatible_items(
        self,
        sku_id: str,
        slot: Optional[str] = None,
        limit: int = 50,
        min_score: float = 0.0,
    ) -> dict[str, list[dict]]:
        """Get compatible items for a given SKU, optionally filtered by slot."""
        if sku_id not in self._graph:
            return {}

        product_graph = self._graph[sku_id]

        if slot:
            slot_lower = slot.lower()
            # Find matching slot (case-insensitive)
            matching_slot = None
            for s in product_graph.keys():
                if s.lower() == slot_lower:
                    matching_slot = s
                    break

            if not matching_slot:
                return {}

            items = [
                item for item in product_graph[matching_slot]
                if item["score"] >= min_score
            ][:limit]
            return {slot_lower: items}

        result = {}
        for slot_name, items in product_graph.items():
            filtered = [item for item in items if item["score"] >= min_score][:limit]
            if filtered:
                result[slot_name.lower()] = filtered

        return result

    async def get_all_compatible(self, sku_id: str) -> dict[str, list[dict]]:
        """Get ALL compatible items for a SKU (used for look generation)."""
        if sku_id not in self._graph:
            return {}

        result = {}
        for slot_name, items in self._graph[sku_id].items():
            result[slot_name.lower()] = items

        return result

    async def get_compatible_with_cross_scores(
        self,
        sku_id: str,
        candidates_per_slot: int = 25
    ) -> tuple[dict[str, list[dict]], dict[tuple[str, str], float]]:
        """
        Get compatible items AND cross-scores.

        Returns:
            - compatible_by_slot: {slot_name: [{"sku": str, "score": float}, ...]}
            - pair_scores: {(sku1, sku2): score}
        """
        if sku_id not in self._graph:
            return {}, {}

        # Get compatible items (limited per slot)
        compatible_by_slot = {}
        all_candidate_skus = set()

        for slot_name, items in self._graph[sku_id].items():
            slot_lower = slot_name.lower()
            limited_items = items[:candidates_per_slot]
            compatible_by_slot[slot_lower] = limited_items
            for item in limited_items:
                all_candidate_skus.add(item["sku"])

        # Build pair scores: base->candidates and candidate->candidate
        pair_scores = {}

        # Base to candidate scores
        for items in compatible_by_slot.values():
            for item in items:
                pair_scores[(sku_id, item["sku"])] = item["score"]
                pair_scores[(item["sku"], sku_id)] = item["score"]

        # Cross-scores between candidates
        for candidate_sku in all_candidate_skus:
            if candidate_sku in self._graph:
                for slot_items in self._graph[candidate_sku].values():
                    for item in slot_items:
                        if item["sku"] in all_candidate_skus:
                            pair_scores[(candidate_sku, item["sku"])] = item["score"]
                            pair_scores[(item["sku"], candidate_sku)] = item["score"]

        return compatible_by_slot, pair_scores

    async def get_pair_score(self, sku1: str, sku2: str) -> Optional[float]:
        """Get the compatibility score between two SKUs."""
        if sku1 not in self._graph:
            return None

        for slot_items in self._graph[sku1].values():
            for item in slot_items:
                if item["sku"] == sku2:
                    return item["score"]
        return None

    async def get_pair_scores_batch(
        self,
        sku1: str,
        sku2_list: list[str]
    ) -> dict[str, float]:
        """Get compatibility scores for sku1 paired with multiple sku2s."""
        if not sku2_list or sku1 not in self._graph:
            return {}

        sku2_set = set(sku2_list)
        result = {}

        for slot_items in self._graph[sku1].values():
            for item in slot_items:
                if item["sku"] in sku2_set:
                    result[item["sku"]] = item["score"]

        return result

    async def calculate_outfit_score(self, sku_ids: list[str]) -> dict:
        """Calculate total outfit score for a list of SKUs."""
        pair_scores = {}
        total_score = 0.0
        pair_count = 0

        for i, sku1 in enumerate(sku_ids):
            for sku2 in sku_ids[i + 1:]:
                score = await self.get_pair_score(sku1, sku2)
                if score is None:
                    # Try reverse
                    score = await self.get_pair_score(sku2, sku1)

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
        """Get graph statistics."""
        if self._metadata:
            return self._metadata

        # Calculate stats if no metadata
        total_edges = sum(
            len(items)
            for product in self._graph.values()
            for items in product.values()
        )
        return {
            "total_edges": total_edges,
            "unique_products": len(self._graph),
            "average_score": 0.0,
        }


# Singleton accessor
_graph_instance: Optional[CompatibilityGraph] = None


async def get_compatibility_graph() -> CompatibilityGraph:
    """Get the singleton compatibility graph service."""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = CompatibilityGraph()
        _graph_instance.load()
    return _graph_instance
