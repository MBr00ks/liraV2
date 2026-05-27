import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, Response
from httpx import AsyncClient, Timeout
from pydantic import BaseModel
from typing import Optional

from src.log import get_logger

logger = get_logger("ollama-proxy")
router = APIRouter()

OLLAMA_BASE = "http://localhost:11434"
_client = AsyncClient(timeout=Timeout(120.0))


class ChatRequest(BaseModel):
    model: str = "mistral-nemo:12b"
    messages: list[dict]
    stream: bool = False
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None


def _build_payload(req: ChatRequest) -> dict:
    payload = {
        "model": req.model,
        "messages": req.messages,
        "stream": req.stream,
        "keep_alive": "5m",
    }
    options = {}
    if req.max_tokens is not None:
        options["num_predict"] = req.max_tokens
    if req.temperature is not None:
        options["temperature"] = req.temperature
    if req.top_p is not None:
        options["top_p"] = req.top_p
    if options:
        payload["options"] = options
    return payload


@router.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    payload = _build_payload(req)

    try:
        response = await _client.post(f"{OLLAMA_BASE}/api/chat", json=payload)
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama error: {e}")

    if req.stream:
        return StreamingResponse(_stream_ollama(response), media_type="text/event-stream")
    else:
        data = response.json()
        content = data.get("message", {}).get("content", "")
        return {
            "id": f"chatcmpl-{id(req)}",
            "object": "chat.completion",
            "model": req.model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        }


async def _stream_ollama(ollama_response):
    chat_id = f"chatcmpl-{id(ollama_response)}"
    async for line in ollama_response.aiter_lines():
        if not line:
            continue
        try:
            chunk = json.loads(line)
            content = chunk.get("message", {}).get("content", "")
            done = chunk.get("done", False)
            payload = {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "choices": [{"index": 0, "delta": {"content": content} if not done else {}, "finish_reason": "stop" if done else None}],
            }
            yield f"data: {json.dumps(payload)}\n\n"
            if done:
                yield "data: [DONE]\n\n"
        except json.JSONDecodeError:
            continue


@router.get("/v1/models")
async def list_models():
    try:
        resp = await _client.get(f"{OLLAMA_BASE}/api/tags")
        resp.raise_for_status()
        data = resp.json()
        models = [{"id": m["name"], "object": "model"} for m in data.get("models", [])]
        return {"object": "list", "data": models}
    except Exception as e:
        return {"object": "list", "data": [{"id": "mistral-nemo:12b", "object": "model"}]}
