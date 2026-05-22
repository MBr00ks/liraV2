import httpx

from src.config import get_settings
from src.logging import get_logger

logger = get_logger("embedding-service")


class EmbeddingService:
    def __init__(self):
        settings = get_settings()
        self.base_url = (settings.ollama_base_url).rstrip("/")
        self.model = settings.ollama_embedding_model
        self._client = httpx.AsyncClient(timeout=30.0)
        logger.info("EmbeddingService initialized", {"model": self.model})

    async def embed(self, text: str) -> list[float]:
        payload = {
            "model": self.model,
            "input": text,
        }
        try:
            response = await self._client.post(f"{self.base_url}/api/embed", json=payload)
            if response.status_code == 200:
                data = response.json()
                embeddings = data.get("embeddings", [])
                if embeddings:
                    return embeddings[0]
        except Exception:
            pass

        payload_old = {
            "model": self.model,
            "prompt": text,
        }
        try:
            response = await self._client.post(f"{self.base_url}/api/embeddings", json=payload_old)
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])
        except Exception as e:
            logger.warn("Embedding failed, using zero vector fallback", {"error": str(e)})
            return [0.0] * 768

    async def close(self):
        await self._client.aclose()


def create_embedding_service() -> EmbeddingService:
    return EmbeddingService()
