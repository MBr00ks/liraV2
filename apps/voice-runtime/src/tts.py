import httpx
import base64
from typing import Optional
from dataclasses import dataclass

from src.config import get_settings
from src.log import get_logger

logger = get_logger("tts")


@dataclass
class TTSResult:
    audio_base64: str
    duration_ms: float
    sample_rate: int
    format: str


class KokoroClient:
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.kokoro_base_url.rstrip("/")
        self.default_voice = settings.kokoro_voice
        self.default_speed = settings.kokoro_speed
        self._client = httpx.AsyncClient(timeout=30.0)
        self._stream_client = httpx.AsyncClient(timeout=60.0)

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
    ) -> TTSResult:
        payload = {
            "text": text,
            "voice": voice or self.default_voice,
            "speed": speed if speed is not None else self.default_speed,
        }

        try:
            response = await self._client.post(f"{self.base_url}/synthesize", json=payload)
            response.raise_for_status()
            result = response.json()

            return TTSResult(
                audio_base64=result["audio"],
                duration_ms=result.get("duration_ms", 0.0),
                sample_rate=result.get("sample_rate", 24000),
                format=result.get("format", "wav"),
            )
        except httpx.HTTPError as e:
            logger.error("Kokoro TTS failed", {"error": str(e), "text_length": len(text)})
            raise RuntimeError(f"TTS service unavailable: {e}")

    async def synthesize_raw(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
    ) -> bytes:
        payload = {
            "input": text,
            "voice": voice or self.default_voice,
            "speed": speed if speed is not None else self.default_speed,
            "response_format": "wav",
        }

        try:
            response = await self._client.post(f"{self.base_url}/v1/audio/speech", json=payload)
            response.raise_for_status()
            return response.content
        except httpx.HTTPError as e:
            logger.error("Kokoro raw TTS failed", {"error": str(e), "text_length": len(text)})
            raise RuntimeError(f"TTS raw unavailable: {e}")

    async def synthesize_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
    ):
        payload = {
            "text": text,
            "voice": voice or self.default_voice,
            "speed": speed if speed is not None else self.default_speed,
            "stream": True,
        }

        try:
            async with self._stream_client.stream("POST", f"{self.base_url}/synthesize", json=payload) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    yield chunk
        except httpx.HTTPError as e:
            logger.error("Kokoro TTS stream failed", {"error": str(e)})
            raise RuntimeError(f"TTS stream unavailable: {e}")

    async def health_check(self) -> bool:
        try:
            response = await self._client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        await self._client.aclose()
        await self._stream_client.aclose()
