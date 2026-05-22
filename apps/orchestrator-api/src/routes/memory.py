import uuid
from fastapi import APIRouter, HTTPException

from src.models import MemoryCreate, MemoryUpdate, MemoryResponse, MemorySearchRequest
from src.logging import get_logger, log_request

logger = get_logger("memory-route")

router = APIRouter()

_memory_writer = None
_memory_retriever = None


def get_memory_writer():
    global _memory_writer
    if _memory_writer is None:
        from src.config import get_settings
        from packages.memory.src.postgres_client import create_postgres_client
        from packages.memory.src.qdrant_client import create_qdrant_client
        from packages.memory.src.memory_writer import MemoryWriter

        settings = get_settings()
        postgres = create_postgres_client()
        qdrant = create_qdrant_client()

        async def embed_fn(text: str) -> list[float]:
            return [0.0] * 768

        _memory_writer = MemoryWriter(postgres, qdrant, embed_fn)
    return _memory_writer


def get_memory_retriever():
    global _memory_retriever
    if _memory_retriever is None:
        from packages.memory.src.postgres_client import create_postgres_client
        from packages.memory.src.qdrant_client import create_qdrant_client
        from packages.memory.src.memory_retriever import MemoryRetriever

        postgres = create_postgres_client()
        qdrant = create_qdrant_client()

        async def embed_fn(text: str) -> list[float]:
            return [0.0] * 768

        _memory_retriever = MemoryRetriever(postgres, qdrant, embed_fn)
    return _memory_retriever


@router.post("/", response_model=MemoryResponse)
async def create_memory(request: MemoryCreate):
    request_id = str(uuid.uuid4())
    log_request(logger, request_id, endpoint="memory", method="POST")

    try:
        writer = get_memory_writer()
        result = await writer.write(request.category, {
            "category": request.category,
            "title": request.title,
            "content": request.content,
            "importance": request.importance,
            "metadata": request.metadata,
            "merge_strategy": "create_new",
        })

        return MemoryResponse(
            id=result.id,
            category=result.category,
            title=request.title,
            content=request.content,
            importance=result.importance,
            metadata=request.metadata,
            created_at="",
            updated_at="",
        )
    except Exception as e:
        logger.error("Memory creation failed", {"request_id": request_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{category}/{memory_id}", response_model=MemoryResponse)
async def get_memory(category: str, memory_id: int):
    request_id = str(uuid.uuid4())
    log_request(logger, request_id, endpoint="memory", method="GET")

    try:
        from packages.memory.src.postgres_client import create_postgres_client

        postgres = create_postgres_client()
        record = await postgres.get_by_id(category, memory_id)

        if not record:
            raise HTTPException(status_code=404, detail="Memory not found")

        return MemoryResponse(
            id=record.id,
            category=record.category,
            title=record.title,
            content=record.content,
            importance=record.importance,
            metadata=record.metadata,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Memory retrieval failed", {"request_id": request_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_memory(request: MemorySearchRequest):
    request_id = str(uuid.uuid4())
    log_request(logger, request_id, endpoint="memory/search", method="POST")

    try:
        retriever = get_memory_retriever()
        results = await retriever.retrieve({
            "query": request.query,
            "categories": request.categories,
            "limit": request.limit,
            "min_importance": 1,
            "include_embeddings": True,
        })

        return {
            "results": [
                {
                    "id": r.id,
                    "category": r.category,
                    "title": r.title,
                    "content": r.content,
                    "importance": r.importance,
                }
                for r in results
            ],
            "total": len(results),
        }
    except Exception as e:
        logger.error("Memory search failed", {"request_id": request_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{category}/{memory_id}")
async def delete_memory(category: str, memory_id: int):
    request_id = str(uuid.uuid4())
    log_request(logger, request_id, endpoint="memory", method="DELETE")

    try:
        from packages.memory.src.postgres_client import create_postgres_client
        from packages.memory.src.qdrant_client import create_qdrant_client

        postgres = create_postgres_client()
        qdrant = create_qdrant_client()

        deleted = await postgres.delete(category, memory_id)
        if deleted:
            await qdrant.delete(f"memory_{memory_id}")

        return {"deleted": deleted}
    except Exception as e:
        logger.error("Memory deletion failed", {"request_id": request_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))
