from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from functools import lru_cache

from src.config import get_settings
from src.logging import get_logger
from src.embedder import Embedder
from src.vector_store import VectorStore
from src.summarizer import Summarizer
from src.st_bridge import SillyTavernBridge
from src.models.memory import MemoryWrite, MemoryEntry, MemoryQuery, ConversationChunk, Realm

logger = get_logger("memory-service")


@lru_cache()
def get_embedder() -> Embedder:
    return Embedder()


@lru_cache()
def get_vector_store() -> VectorStore:
    return VectorStore()


@lru_cache()
def get_summarizer() -> Summarizer:
    return Summarizer()


@lru_cache()
def get_st_bridge() -> SillyTavernBridge:
    return SillyTavernBridge()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Memory service starting")
    yield
    logger.info("Memory service shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Lira V2 Memory Service",
        description="Persistent memory with vector search for Lira",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/memory", status_code=201)
    async def write_memory(memory: MemoryWrite):
        emb = get_embedder()
        vs = get_vector_store()
        vector = await emb.embed(memory.content)
        entry = MemoryEntry(
            category=memory.category,
            title=memory.title,
            content=memory.content,
            realm=memory.realm,
            importance=memory.importance,
            source=memory.source,
            metadata=memory.metadata,
        )
        memory_id = await vs.upsert(entry, vector)
        logger.info("Memory written", memory_id=memory_id, category=memory.category.value)
        return {"id": memory_id, "status": "stored"}

    @app.post("/memory/query")
    async def query_memories(query: MemoryQuery):
        emb = get_embedder()
        vs = get_vector_store()
        vector = await emb.embed(query.text)
        results = await vs.search(
            vector=vector,
            realm=query.realm,
            category=query.category,
            limit=query.limit,
            min_importance=query.min_importance,
        )
        return {
            "results": [
                {
                    "id": r.id,
                    "title": r.title,
                    "content": r.content,
                    "category": r.category.value,
                    "realm": r.realm.value,
                    "importance": r.importance,
                    "score": r.score,
                    "created_at": r.created_at.isoformat(),
                }
                for r in results
            ],
            "count": len(results),
        }

    @app.post("/memory/summarize")
    async def summarize_conversation(chunk: ConversationChunk):
        summ = get_summarizer()
        emb = get_embedder()
        vs = get_vector_store()
        summary, category = await summ.summarize(chunk)
        vector = await emb.embed(summary)

        entry = MemoryEntry(
            category=category,
            title=f"{chunk.realm.value} session: {chunk.messages[0].timestamp.strftime('%b %d')}" if chunk.messages else "Conversation",
            content=summary,
            realm=chunk.realm,
            importance=3,
            source="chat_summary",
            metadata={
                "session_id": chunk.session_id,
                "message_count": len(chunk.messages),
            },
        )
        memory_id = await vs.upsert(entry, vector)

        return {
            "memory_id": memory_id,
            "summary": summary,
            "category": category.value,
            "title": entry.title,
        }

    @app.get("/memory/stats")
    async def memory_stats():
        vs = get_vector_store()
        count = await vs.count()
        return {"total_memories": count, "collection": vs.collection}

    @app.get("/memory/{memory_id}")
    async def get_memory(memory_id: str):
        vs = get_vector_store()
        results = await vs.search(
            vector=[0.0] * 768,
            limit=100,
        )
        for r in results:
            if r.id == memory_id:
                return {
                    "id": r.id,
                    "title": r.title,
                    "content": r.content,
                    "category": r.category.value,
                    "realm": r.realm.value,
                    "importance": r.importance,
                    "created_at": r.created_at.isoformat(),
                }
        raise HTTPException(status_code=404, detail="Memory not found")

    @app.delete("/memory/{memory_id}")
    async def delete_memory(memory_id: str):
        vs = get_vector_store()
        await vs.delete(memory_id)
        return {"status": "deleted"}

    @app.post("/memory/inject")
    async def inject_memories(query: MemoryQuery):
        bridge = get_st_bridge()
        emb = get_embedder()
        vs = get_vector_store()
        character = await bridge.get_active_character()
        if not character:
            raise HTTPException(status_code=400, detail="No active character found in ST")

        vector = await emb.embed(query.text)
        results = await vs.search(
            vector=vector,
            realm=query.realm,
            category=query.category,
            limit=query.limit,
        )

        if not results:
            return {"injected": False, "reason": "no relevant memories", "character": character}

        note_parts = ["[MEMORIES]"]
        for r in results:
            note_parts.append(f"- {r.title}: {r.content}")
        note = "\n".join(note_parts)

        success = await bridge.set_character_note(character, note)
        return {
            "injected": success,
            "character": character,
            "memory_count": len(results),
            "note_preview": note[:200],
        }

    @app.get("/health")
    async def health():
        vs = get_vector_store()
        qdrant_ok = await vs.health_check()
        return {
            "status": "ok" if qdrant_ok else "degraded",
            "service": "lira-memory-service",
            "version": "0.1.0",
            "qdrant": "ok" if qdrant_ok else "unreachable",
            "stored_memories": await vs.count() if qdrant_ok else 0,
        }

    return app


app = create_app()
