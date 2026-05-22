import uuid
import json
import asyncio
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from src.models import ChatRequest, ChatResponse, StreamChunk
from src.logging import get_logger, log_request, log_latency

logger = get_logger("chat-route")

router = APIRouter()

_companion_loop = None


def get_companion_loop():
    global _companion_loop
    if _companion_loop is None:
        from src.companion_loop import CompanionLoop
        from src.emotion_engine import EmotionEngine
        from src.ollama_client import OllamaClient
        from src.postgres_client import create_postgres_client
        from src.qdrant_client import create_qdrant_client
        from src.embedding_service import create_embedding_service
        from src.memory_writer import MemoryWriter
        from src.memory_retriever import MemoryRetriever

        emotion_engine = EmotionEngine()
        model_client = OllamaClient()
        postgres = create_postgres_client()
        qdrant = create_qdrant_client()
        embed_service = create_embedding_service()

        async def embed_fn(text: str) -> list[float]:
            return await embed_service.embed(text)

        memory_writer = MemoryWriter(postgres, qdrant, embed_fn)
        memory_retriever = MemoryRetriever(postgres, qdrant, embed_fn)

        _companion_loop = CompanionLoop(
            emotion_engine=emotion_engine,
            model_client=model_client,
            memory_retriever=memory_retriever,
            memory_writer=memory_writer,
        )
    return _companion_loop


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    request_id = str(uuid.uuid4())
    log_request(logger, request_id, endpoint="chat", method="POST")

    try:
        loop = get_companion_loop()
        response = await loop.process_message(
            message=request.message,
            session_id=request.session_id,
            mode=request.mode,
        )

        log_latency(logger, request_id, model=response.model_used, latency_ms=response.latency_ms)

        return ChatResponse(
            content=response.content,
            session_id=request.session_id or str(uuid.uuid4()),
            realm=response.realm,
            emotion=response.emotion,
            intensity=response.intensity,
            prosody_mode=response.prosody_mode,
            model_used=response.model_used,
            latency_ms=response.latency_ms,
            internal_thoughts=response.internal_thoughts,
            avatar_signal=response.avatar_signal,
            sfx_event=response.sfx_event,
            spoken_text=response.spoken_text,
        )
    except Exception as e:
        logger.error("Chat failed", {"request_id": request_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    request_id = str(uuid.uuid4())
    log_request(logger, request_id, endpoint="chat/stream", method="POST", stream=True)

    async def event_generator():
        try:
            loop = get_companion_loop()
            async for chunk in loop.process_stream(
                message=request.message,
                session_id=request.session_id,
                mode=request.mode,
            ):
                chunk_type = chunk.get("type", "content")
                if chunk_type == "avatar_signal":
                    yield {
                        "event": "avatar_signal",
                        "data": json.dumps(chunk.get("payload", {})),
                    }
                elif chunk_type == "sfx_event":
                    yield {
                        "event": "sfx_event",
                        "data": json.dumps(chunk.get("payload", {})),
                    }
                elif chunk_type == "content":
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "content": chunk.get("content", ""),
                            "done": chunk.get("done", False),
                            "spoken_text": chunk.get("spoken_text"),
                        }),
                    }
                    if chunk.get("done"):
                        break
        except Exception as e:
            logger.error("Stream failed", {"request_id": request_id, "error": str(e)})
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }

    return EventSourceResponse(event_generator())
