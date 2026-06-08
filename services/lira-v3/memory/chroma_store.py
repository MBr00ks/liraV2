"""ChromaDB-backed semantic memory store with metadata filtering."""
from uuid import uuid4

import chromadb

from shared.settings import settings
from .embedding import embed

COLLECTIONS = ["identity", "relationship", "projects", "episodes", "lore"]


class ChromaMemoryStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self._cols = {}
        for name in COLLECTIONS:
            self._cols[name] = self.client.get_or_create_collection(
                f"lira_{name}",
                metadata={"hnsw:space": "cosine"},
            )

    async def store(self, collection: str, text: str, metadata: dict | None = None):
        """Store a text with embedding in the given collection."""
        if collection not in self._cols:
            raise ValueError(f"Unknown collection: {collection}")
        embedding = (await embed(text))[0]
        # ChromaDB metadata must be string values
        safe_meta = {k: str(v) for k, v in (metadata or {}).items()}
        self._cols[collection].add(
            embeddings=[embedding],
            documents=[text],
            metadatas=[safe_meta],
            ids=[str(uuid4())],
        )

    async def query(self, text: str, collection: str | None = None, k: int = 5) -> list[dict]:
        """Semantic search across collections."""
        embedding = (await embed(text))[0]
        cols = [self._cols[collection]] if collection else list(self._cols.values())
        results = []
        for col in cols:
            if col.count() == 0:
                continue
            r = col.query(query_embeddings=[embedding], n_results=k)
            for i in range(len(r["ids"][0])):
                results.append({
                    "id": r["ids"][0][i],
                    "document": r["documents"][0][i] if r["documents"] else "",
                    "metadata": r["metadatas"][0][i] if r["metadatas"] else {},
                    "distance": r["distances"][0][i] if r["distances"] else 0,
                })
        results.sort(key=lambda x: x["distance"])
        return results[:k]

    async def delete(self, collection: str, doc_id: str):
        if collection in self._cols:
            self._cols[collection].delete(ids=[doc_id])

    def count(self, collection: str | None = None) -> int:
        if collection:
            return self._cols[collection].count() if collection in self._cols else 0
        return sum(col.count() for col in self._cols.values())
