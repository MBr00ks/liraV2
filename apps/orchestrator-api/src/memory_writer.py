from typing import Callable, Optional
import uuid

from src.postgres_client import PostgresClient
from src.qdrant_client import QdrantClient
from src.logging import get_logger

logger = get_logger("memory-writer")

EmbedFn = Callable[[str], list[float]]


class MemoryWriter:
    def __init__(self, postgres: PostgresClient, qdrant: QdrantClient, embed_fn: EmbedFn):
        self.postgres = postgres
        self.qdrant = qdrant
        self.embed_fn = embed_fn
        self.collection = "memories"

    async def write(self, category: str, data: dict) -> dict:
        title = data.get("title", "")
        content = data.get("content", "")
        importance = data.get("importance", 3)
        metadata = data.get("metadata", {})
        merge_strategy = data.get("merge_strategy", "create_new")

        if merge_strategy == "create_new":
            return await self._create(category, title, content, importance, metadata)
        elif merge_strategy == "update_existing":
            memory_id = data.get("id")
            if memory_id:
                return await self._update(category, memory_id, title, content, importance, metadata)
            return await self._create(category, title, content, importance, metadata)
        else:
            return await self._create(category, title, content, importance, metadata)

    async def _create(self, category: str, title: str, content: str, importance: int, metadata: dict) -> dict:
        result = await self.postgres.insert(category, title, content, importance, metadata)
        memory_id = result["id"]

        try:
            embedding = await self.embed_fn(f"{title} {content}")
            point_id = f"memory_{memory_id}"
            await self.qdrant.upsert(self.collection, point_id, embedding, {
                "category": category,
                "title": title,
                "content": content,
                "importance": importance,
                "metadata": metadata,
            })
        except Exception as e:
            logger.warn("Qdrant upsert failed, memory still stored in Postgres", {"error": str(e)})

        return {"id": memory_id, "category": category, "title": title, "importance": importance}

    async def _update(self, category: str, memory_id: int, title: Optional[str], content: Optional[str], importance: Optional[int], metadata: Optional[dict]) -> dict:
        result = await self.postgres.update(category, memory_id, title, content, importance, metadata)
        if not result:
            raise ValueError(f"Memory {memory_id} not found in category {category}")

        try:
            if content or title:
                embedding = await self.embed_fn(f"{title or ''} {content or ''}")
                point_id = f"memory_{memory_id}"
                await self.qdrant.upsert(self.collection, point_id, embedding, {
                    "category": category,
                    "title": title,
                    "content": content,
                    "importance": importance,
                    "metadata": metadata,
                })
        except Exception as e:
            logger.warn("Qdrant update failed", {"error": str(e)})

        return result
