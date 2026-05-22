import asyncpg
import json
from typing import Optional
from datetime import datetime, timezone

from src.config import get_settings
from src.logging import get_logger

logger = get_logger("postgres-client")


class PostgresClient:
    def __init__(self):
        settings = get_settings()
        self.dsn = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        self._pool: Optional[asyncpg.Pool] = None
        logger.info("PostgresClient initialized", {"host": settings.postgres_host, "db": settings.postgres_db})

    async def connect(self):
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.dsn, min_size=2, max_size=10)
            await self._init_tables()
            logger.info("Postgres connection pool created")

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def _init_tables(self):
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id SERIAL PRIMARY KEY,
                    category VARCHAR(50) NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance INTEGER NOT NULL DEFAULT 3,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
                CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance);
                CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at DESC);
            """)

    async def insert(self, category: str, title: str, content: str, importance: int = 3, metadata: dict = None) -> dict:
        await self.connect()
        metadata_json = json.dumps(metadata) if metadata else "{}"
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO memories (category, title, content, importance, metadata) VALUES ($1, $2, $3, $4, $5) RETURNING id, created_at",
                category, title, content, importance, metadata_json,
            )
            return {"id": row["id"], "created_at": row["created_at"].isoformat()}

    async def get_by_id(self, category: str, memory_id: int) -> Optional[dict]:
        await self.connect()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, category, title, content, importance, metadata, created_at, updated_at FROM memories WHERE category = $1 AND id = $2",
                category, memory_id,
            )
            if not row:
                return None
            return {
                "id": row["id"],
                "category": row["category"],
                "title": row["title"],
                "content": row["content"],
                "importance": row["importance"],
                "metadata": json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"],
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
            }

    async def search_by_category(self, category: str, limit: int = 10, min_importance: int = 1) -> list[dict]:
        await self.connect()
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, category, title, content, importance, metadata, created_at, updated_at FROM memories WHERE category = $1 AND importance >= $2 ORDER BY importance DESC, created_at DESC LIMIT $3",
                category, min_importance, limit,
            )
            return [
                {
                    "id": r["id"],
                    "category": r["category"],
                    "title": r["title"],
                    "content": r["content"],
                    "importance": r["importance"],
                    "metadata": json.loads(r["metadata"]) if isinstance(r["metadata"], str) else r["metadata"],
                    "created_at": r["created_at"].isoformat(),
                    "updated_at": r["updated_at"].isoformat(),
                }
                for r in rows
            ]

    async def update(self, category: str, memory_id: int, title: Optional[str] = None, content: Optional[str] = None, importance: Optional[int] = None, metadata: Optional[dict] = None) -> Optional[dict]:
        await self.connect()
        updates = []
        values = []
        idx = 1
        if title is not None:
            updates.append(f"title = ${idx}")
            values.append(title)
            idx += 1
        if content is not None:
            updates.append(f"content = ${idx}")
            values.append(content)
            idx += 1
        if importance is not None:
            updates.append(f"importance = ${idx}")
            values.append(importance)
            idx += 1
        if metadata is not None:
            updates.append(f"metadata = ${idx}")
            values.append(json.dumps(metadata))
            idx += 1
        if not updates:
            return None
        updates.append(f"updated_at = NOW()")
        values.extend([category, memory_id])
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"UPDATE memories SET {', '.join(updates)} WHERE category = ${idx} AND id = ${idx + 1} RETURNING id, updated_at",
                *values,
            )
            if not row:
                return None
            return {"id": row["id"], "updated_at": row["updated_at"].isoformat()}

    async def delete(self, category: str, memory_id: int) -> bool:
        await self.connect()
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM memories WHERE category = $1 AND id = $2",
                category, memory_id,
            )
            return result == "DELETE 1"


def create_postgres_client() -> PostgresClient:
    return PostgresClient()
