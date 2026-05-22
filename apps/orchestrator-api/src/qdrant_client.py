from typing import Optional
import httpx

from src.config import get_settings
from src.logging import get_logger

logger = get_logger("qdrant-client")


class QdrantClient:
    def __init__(self):
        settings = get_settings()
        self.host = settings.qdrant_host
        self.port = settings.qdrant_port
        self.api_key = settings.qdrant_api_key if settings.qdrant_api_key else None
        self.base_url = f"http://{self.host}:{self.port}"
        self._client = httpx.AsyncClient(timeout=30.0)
        self._headers = {"api-key": self.api_key} if self.api_key else {}
        logger.info("QdrantClient initialized", {"host": self.host, "port": self.port, "has_api_key": bool(self.api_key)})

    async def upsert(self, collection: str, point_id: str, vector: list[float], payload: dict) -> bool:
        await self._ensure_collection(collection, len(vector))
        url = f"{self.base_url}/collections/{collection}/points?wait=true"
        body = {
            "points": [
                {
                    "id": point_id,
                    "vector": vector,
                    "payload": payload,
                }
            ]
        }
        try:
            response = await self._client.put(url, json=body, headers=self._headers)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error("Qdrant upsert failed", {"error": str(e)})
            return False

    async def _ensure_collection(self, collection: str, vector_size: int):
        url = f"{self.base_url}/collections/{collection}"
        try:
            response = await self._client.get(url, headers=self._headers)
            if response.status_code == 404:
                create_url = f"{self.base_url}/collections/{collection}"
                create_body = {
                    "vectors": {
                        "size": vector_size,
                        "distance": "Cosine",
                    }
                }
                response = await self._client.put(create_url, json=create_body, headers=self._headers)
                response.raise_for_status()
                logger.info("Qdrant collection created", {"collection": collection, "vector_size": vector_size})
        except Exception as e:
            logger.warn("Qdrant collection check failed", {"error": str(e)})

    async def search(self, collection: str, vector: list[float], limit: int = 5, filter_payload: Optional[dict] = None) -> list[dict]:
        url = f"{self.base_url}/collections/{collection}/points/search"
        body = {
            "vector": vector,
            "limit": limit,
            "with_payload": True,
        }
        if filter_payload:
            body["filter"] = {
                "must": [{"key": k, "match": {"value": v}} for k, v in filter_payload.items()]
            }
        try:
            response = await self._client.post(url, json=body, headers=self._headers)
            response.raise_for_status()
            data = response.json()
            return [
                {
                    "id": p["id"],
                    "score": p["score"],
                    **p.get("payload", {}),
                }
                for p in data.get("result", [])
            ]
        except Exception as e:
            logger.error("Qdrant search failed", {"error": str(e)})
            return []

    async def delete(self, point_id: str, collection: str = "memories") -> bool:
        url = f"{self.base_url}/collections/{collection}/points/delete"
        body = {"points": [point_id]}
        try:
            response = await self._client.post(url, json=body, headers=self._headers)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error("Qdrant delete failed", {"error": str(e)})
            return False

    async def close(self):
        await self._client.aclose()


def create_qdrant_client() -> QdrantClient:
    return QdrantClient()
