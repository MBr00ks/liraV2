import httpx
from src.config import get_settings
from src.logging import get_logger

logger = get_logger("embedder")


class Embedder:
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_embedding_model

    async def embed(self, text: str) -> list[float]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": self.model, "input": text},
                )
                response.raise_for_status()
                result = response.json()

            embeddings = result.get("embeddings", [])
            if not embeddings:
                logger.warning("No embeddings returned", {"text_length": len(text)})
                return [0.0] * 768

            return embeddings[0]

        except httpx.HTTPError as e:
            logger.error("Embedding failed", {"error": str(e)})
            raise RuntimeError(f"Embedding service unavailable: {e}")

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": self.model, "input": texts},
                )
                response.raise_for_status()
                result = response.json()

            return result.get("embeddings", [])

        except httpx.HTTPError as e:
            logger.error("Batch embedding failed", {"error": str(e), "count": len(texts)})
            raise RuntimeError(f"Embedding service unavailable: {e}")
