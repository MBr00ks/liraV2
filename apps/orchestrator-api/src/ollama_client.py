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
        self._client = httpx.AsyncClient(timeout=120.0)
        logger.info("OllamaClient initialized", {"base_url": self.base_url, "model": self.model})

    async def chat(self, messages: list[dict[str, str]], temperature: float = 0.7, max_tokens: int = 2048) -> dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "think": False,
            },
        }
        logger.info("Ollama chat request", {"model": self.model, "message_count": len(messages)})
        logger.debug("Messages sent to Ollama", {"messages": messages})

        try:
            response = await self._client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            content = data.get("message", {}).get("content", "")
            return {"content": content, "model": self.model}
        except httpx.HTTPStatusError as e:
            logger.error("Ollama HTTP error", {"status": e.response.status_code, "body": e.response.text})
            raise
        except Exception as e:
            logger.error("Ollama request failed", {"error": str(e)})
            raise

    async def stream_chat(self, messages: list[dict[str, str]], temperature: float = 0.7, max_tokens: int = 2048) -> AsyncGenerator[dict, None]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "think": False,
            },
        }
        logger.info("Ollama stream chat request", {"model": self.model})

        try:
            async with self._client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        done = chunk.get("done", False)
                        yield {"content": content, "done": done}
                        if done:
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error("Ollama stream failed", {"error": str(e)})
            yield {"content": "", "done": True}

    async def close(self):
        await self._client.aclose()
