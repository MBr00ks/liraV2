import uuid
import json
import time
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from src.models import ChatRequest
from src.logging import get_logger

logger = get_logger("openai-compat")

router = APIRouter()


def get_companion_loop():
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

    return CompanionLoop(
        emotion_engine=emotion_engine,
        model_client=model_client,
        memory_retriever=memory_retriever,
        memory_writer=memory_writer,
    )


@router.get("/models")
async def list_models():
    return {
        "object": "list",
        "data": [{
            "id": "qwen3:8b",
            "object": "model",
            "created": 1700000000,
            "owned_by": "ollama",
        }],
    }


@router.post("/chat/completions")
async def openai_chat(request: dict):
    messages = request.get("messages", [])
    stream = request.get("stream", False)
    model = request.get("model", "qwen3:8b")

    last_user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_message = msg.get("content", "")
            break

    recent_history = []
    for msg in messages[-6:]:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role in ("user", "assistant"):
            recent_history.append({"role": role, "content": content})

    chat_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())

    loop = get_companion_loop()

    if stream:
        async def event_generator():
            try:
                async for chunk in loop.process_stream(message=last_user_message, history=recent_history):
                    chunk_type = chunk.get("type", "content")
                    if chunk_type == "content":
                        content = chunk.get("content", "")
                        done = chunk.get("done", False)
                        payload = {
                            "id": chat_id,
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": content} if not done else {},
                                "finish_reason": "stop" if done else None,
                            }],
                        }
                        yield {"data": json.dumps(payload)}
                        if done:
                            yield {"data": "[DONE]"}
                            break
            except Exception as e:
                logger.error("Stream failed", {"error": str(e)})
                yield {"data": json.dumps({"error": str(e)})}
                yield {"data": "[DONE]"}

        return EventSourceResponse(event_generator())

    response = await loop.process_message(message=last_user_message, history=recent_history)

    return {
        "id": chat_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": response.content},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
