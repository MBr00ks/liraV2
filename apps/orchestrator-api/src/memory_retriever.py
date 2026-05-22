from typing import Callable, Optional

from src.postgres_client import PostgresClient
from src.qdrant_client import QdrantClient
from src.logging import get_logger

logger = get_logger("memory-retriever")

EmbedFn = Callable[[str], list[float]]


class MemoryRetriever:
    def __init__(self, postgres: PostgresClient, qdrant: QdrantClient, embed_fn: EmbedFn):
        self.postgres = postgres
        self.qdrant = qdrant
        self.embed_fn = embed_fn

    async def retrieve(self, query: dict) -> list[dict]:
        text_query = query.get("query", "")
        categories = query.get("categories")
        limit = query.get("limit", 10)
        min_importance = query.get("min_importance", 1)

        if text_query and categories:
            return await self._hybrid_search(text_query, categories, limit, min_importance)
        elif categories:
            return await self._category_search(categories[0], limit, min_importance)
        elif text_query:
            return await self._vector_search(text_query, limit, min_importance)
        else:
            return []

    async def _hybrid_search(self, query: str, categories: list[str], limit: int, min_importance: int) -> list[dict]:
        try:
            embedding = await self.embed_fn(query)
            filter_payload = {"category": categories[0]} if len(categories) == 1 else None
            vector_results = await self.qdrant.search("memories", embedding, limit=limit * 2, filter_payload=filter_payload)

            seen_ids = set()
            results = []
            for r in vector_results:
                if r["id"] not in seen_ids and r.get("importance", 0) >= min_importance:
                    seen_ids.add(r["id"])
                    results.append(r)
                    if len(results) >= limit:
                        break

            if len(results) < limit:
                for cat in categories:
                    pg_results = await self.postgres.search_by_category(cat, limit=limit - len(results), min_importance=min_importance)
                    for r in pg_results:
                        if r["id"] not in seen_ids:
                            seen_ids.add(r["id"])
                            results.append(r)
                            if len(results) >= limit:
                                break
                    if len(results) >= limit:
                        break

            return results[:limit]
        except Exception as e:
            logger.warn("Hybrid search failed, falling back to category search", {"error": str(e)})
            return await self._category_search(categories[0], limit, min_importance)

    async def _category_search(self, category: str, limit: int, min_importance: int) -> list[dict]:
        return await self.postgres.search_by_category(category, limit, min_importance)

    async def _vector_search(self, query: str, limit: int, min_importance: int) -> list[dict]:
        try:
            embedding = await self.embed_fn(query)
            results = await self.qdrant.search("memories", embedding, limit=limit)
            return [r for r in results if r.get("importance", 0) >= min_importance][:limit]
        except Exception as e:
            logger.warn("Vector search failed", {"error": str(e)})
            return []
