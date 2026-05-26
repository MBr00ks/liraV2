from datetime import datetime
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    Range,
)

from src.config import get_settings
from src.models.memory import MemoryEntry, MemoryCategory, Realm
from src.logging import get_logger

logger = get_logger("vector-store")


class VectorStore:
    def __init__(self):
        settings = get_settings()
        self.collection = settings.qdrant_collection
        self.client = QdrantClient(
            url=f"http://{settings.qdrant_host}:{settings.qdrant_port}",
            api_key=settings.qdrant_api_key,
        )
        self._ensure_collection()

    def _ensure_collection(self):
        collections = self.client.get_collections().collections
        names = [c.name for c in collections]

        if self.collection not in names:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )
            logger.info("Created collection", collection=self.collection)

    async def upsert(self, entry: MemoryEntry, vector: list[float]) -> str:
        point = PointStruct(
            id=entry.id,
            vector=vector,
            payload={
                "category": entry.category.value,
                "title": entry.title,
                "content": entry.content,
                "realm": entry.realm.value,
                "importance": entry.importance,
                "source": entry.source.value,
                "metadata": entry.metadata,
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat(),
            },
        )
        self.client.upsert(collection_name=self.collection, points=[point])
        return entry.id

    async def search(
        self,
        vector: list[float],
        realm: Optional[Realm] = None,
        category: Optional[MemoryCategory] = None,
        limit: int = 5,
        min_importance: int = 1,
    ) -> list[MemoryEntry]:
        conditions = []

        if realm:
            conditions.append(FieldCondition(key="realm", match=MatchValue(value=realm.value)))

        if category:
            conditions.append(FieldCondition(key="category", match=MatchValue(value=category.value)))

        conditions.append(
            FieldCondition(key="importance", range=Range(gte=min_importance))
        )

        query_filter = Filter(must=conditions) if conditions else None

        response = self.client.query_points(
            collection_name=self.collection,
            query=vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )

        entries = []
        for hit in response.points:
            payload = hit.payload
            entries.append(MemoryEntry(
                id=str(hit.id),
                category=MemoryCategory(payload.get("category", "episodic")),
                title=payload.get("title", ""),
                content=payload.get("content", ""),
                realm=Realm(payload.get("realm", "assistant")),
                importance=payload.get("importance", 3),
                source=payload.get("source", "chat_summary"),
                metadata=payload.get("metadata", {}),
                created_at=datetime.fromisoformat(payload.get("created_at", datetime.utcnow().isoformat())),
                score=hit.score,
            ))

        return entries

    async def delete(self, memory_id: str) -> bool:
        self.client.delete(
            collection_name=self.collection,
            points_selector=[memory_id],
        )
        return True

    async def count(self) -> int:
        result = self.client.count(collection_name=self.collection)
        return result.count

    async def health_check(self) -> bool:
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False
