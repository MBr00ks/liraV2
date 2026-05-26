import httpx
from typing import Optional
from src.config import get_settings
from src.logging import get_logger

logger = get_logger("st-bridge")


class SillyTavernBridge:
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.st_base_url.rstrip("/")
        self.api_key = settings.st_api_key

    async def get_chat_messages(self, character_name: str, limit: int = 20) -> list[dict]:
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/characters/{character_name}/messages",
                    params={"limit": limit},
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.warning("Failed to fetch ST messages", {"error": str(e)})
            return []

    async def set_character_note(self, character_name: str, note: str) -> bool:
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.put(
                    f"{self.base_url}/api/characters/{character_name}",
                    json={"data": {"character_note": note}},
                    headers=headers,
                )
                return response.is_success
        except Exception as e:
            logger.warning("Failed to set character note", {"error": str(e)})
            return False

    async def get_active_character(self) -> Optional[str]:
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/characters/current",
                    headers=headers,
                )
                if response.is_success:
                    data = response.json()
                    return data.get("name")
        except Exception as e:
            logger.debug("Could not get active character", {"error": str(e)})
        return None

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/")
                return response.is_success
        except Exception:
            return False
