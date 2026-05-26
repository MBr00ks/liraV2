import json
import httpx
from typing import Optional, AsyncGenerator

from src.config import get_settings
from src.logging import get_logger

logger = get_logger("ollama-client")


class OllamaClient:
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        settings = get_settings()
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.keep_alive = settings.ollama_keep_alive
        self._client = httpx.AsyncClient(timeout=120.0)
        logger.info("OllamaClient initialized", {"base_url": self.base_url, "model": self.model})

    async def chat(self, messages: list[dict[str, str]], temperature: float = 0.7, max_tokens: int = 2048) -> dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "think": False,
            },
        }

    async def stream_chat(self, messages: list[dict[str, str]], temperature: float = 0.7, max_tokens: int = 2048) -> AsyncGenerator[dict, None]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "think": False,
            },
        }

    async def warmup(self) -> bool:
        """Pre-load the model into Ollama's memory with a minimal request."""
        try:
            response = await self._client.post(f"{self.base_url}/api/generate", json={
                "model": self.model,
                "prompt": "Hello",
                "keep_alive": self.keep_alive,
                "stream": False,
                "options": {"num_predict": 1},
            })
            response.raise_for_status()
            logger.info("Ollama model warmed up", {"model": self.model})
            return True
        except Exception as e:
            logger.warn("Ollama warmup failed", {"error": str(e)})
            return False

    async def close(self):
        await self._client.aclose()
