import json
from pathlib import Path
from typing import Optional
from functools import lru_cache

from app.config import get_settings

settings = get_settings()


class CompatibilityGraph:
    _instance: Optional["CompatibilityGraph"] = None
    _graph: dict = {}
    _metadata: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, path: Optional[str] = None):
        if path is None:
            path = settings.compatibility_graph_path

        graph_path = Path(path)
        if not graph_path.is_absolute():
            graph_path = Path(__file__).parent.parent.parent / path

        with open(graph_path, "r") as f:
            data = json.load(f)

        self._metadata = data.get("metadata", {})
        self._graph = data.get("graph", {})

    @property
    def metadata(self) -> dict:
        return self._metadata

    @property
    def graph(self) -> dict:
        return self._graph

    def get_compatible_items(
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
            if slot not in product_graph:
                return {}
            items = [
                item for item in product_graph[slot] if item["score"] >= min_score
            ][:limit]
            return {slot: items}

        result = {}
        for slot_name, items in product_graph.items():
            filtered = [item for item in items if item["score"] >= min_score][:limit]
            if filtered:
                result[slot_name] = filtered

        return result

    def get_pair_score(self, sku1: str, sku2: str) -> Optional[float]:
        """Get the compatibility score between two SKUs."""
        if sku1 not in self._graph:
            return None

        for slot_items in self._graph[sku1].values():
            for item in slot_items:
                if item["sku"] == sku2:
                    return item["score"]
        return None

    def calculate_outfit_score(self, sku_ids: list[str]) -> dict:
        """Calculate total outfit score for a list of SKUs."""
        pair_scores = {}
        total_score = 0.0
        pair_count = 0

        for i, sku1 in enumerate(sku_ids):
            for sku2 in sku_ids[i + 1 :]:
                score = self.get_pair_score(sku1, sku2)
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

    def get_stats(self) -> dict:
        """Get graph statistics."""
        return self._metadata


@lru_cache
def get_compatibility_graph() -> CompatibilityGraph:
    graph = CompatibilityGraph()
    graph.load()
    return graph
