"""LLM client with local Ollama primary + OpenRouter cloud fallback."""
import json
import logging
import time
from typing import AsyncGenerator

import httpx

from shared.settings import settings

logger = logging.getLogger("llm-client")


class LLMClient:
    def __init__(self):
        self._ollama_url = f"{settings.ollama_base_url}/v1/chat/completions"
        self._model = settings.ollama_model
        self._fallback_key = settings.openrouter_api_key
        self._fallback_model = settings.openrouter_fallback_model
        self._threshold_ms = settings.llm_fallback_threshold_ms

    async def stream(self, system_prompt: str, messages: list[dict[str, str]]) -> AsyncGenerator[str | None, None]:
        """Stream from Ollama, falling back to OpenRouter if latency exceeds threshold."""
        full_messages = [{"role": "system", "content": system_prompt}] + messages

        # Try local Ollama first
        try:
            start = time.monotonic()
            first_token = False
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST", self._ollama_url,
                    json={"model": self._model, "messages": full_messages, "stream": True},
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        payload = line[6:].strip()
                        if payload == "[DONE]":
                            return
                        if not first_token:
                            latency_ms = (time.monotonic() - start) * 1000
                            first_token = True
                            logger.debug(f"Ollama first token: {latency_ms:.0f}ms")
                            if latency_ms > self._threshold_ms and self._fallback_key:
                                logger.warning(f"Ollama slow ({latency_ms:.0f}ms), switching to cloud")
                                yield None  # Signal fallback
                                return
                        try:
                            chunk = json.loads(payload)
                            delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if delta:
                                yield delta
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Ollama failed: {e}, falling back to cloud")
            if self._fallback_key:
                yield None  # Signal fallback
            else:
                raise

    async def stream_fallback(self, system_prompt: str, messages: list[dict[str, str]]) -> AsyncGenerator[str, None]:
        """Stream from OpenRouter cloud fallback."""
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST", "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._fallback_key}",
                    "HTTP-Referer": f"http://localhost:{settings.port}",
                    "X-Title": "Lira V2.5",
                },
                json={
                    "model": self._fallback_model,
                    "messages": full_messages,
                    "stream": True,
                    },
            ) as resp:
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:].strip()
                    if payload == "[DONE]":
                        return
                    try:
                        chunk = json.loads(payload)
                        delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if delta:
                            yield delta
                    except json.JSONDecodeError:
                        continue
