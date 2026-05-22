import httpx
import base64
from typing import Optional
from dataclasses import dataclass

from src.config import get_settings
from src.logging import get_logger

logger = get_logger("stt")


@dataclass
class TranscriptionResult:
    text: str
    confidence: float
    language: str
    duration_ms: float


class WhisperClient:
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.whisper_base_url.rstrip("/")

    async def transcribe_file(self, audio_path: str, language: Optional[str] = None) -> TranscriptionResult:
        try:
            with open(audio_path, "rb") as f:
                audio_data = f.read()

            files = {"file": ("audio.wav", audio_data, "audio/wav")}
            data = {}
            if language:
                data["language"] = language

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{self.base_url}/transcribe", files=files, data=data)
                response.raise_for_status()
                result = response.json()

            return TranscriptionResult(
                text=result.get("text", ""),
                confidence=result.get("confidence", 0.0),
                language=result.get("language", "en"),
                duration_ms=result.get("duration_ms", 0.0),
            )
        except httpx.HTTPError as e:
            logger.error("Whisper transcription failed", {"error": str(e)})
            raise RuntimeError(f"STT service unavailable: {e}")

    async def transcribe_base64(self, audio_b64: str, language: Optional[str] = None) -> TranscriptionResult:
        try:
            audio_data = base64.b64decode(audio_b64)

            files = {"file": ("audio.wav", audio_data, "audio/wav")}
            data = {}
            if language:
                data["language"] = language

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{self.base_url}/transcribe", files=files, data=data)
                response.raise_for_status()
                result = response.json()

            return TranscriptionResult(
                text=result.get("text", ""),
                confidence=result.get("confidence", 0.0),
                language=result.get("language", "en"),
                duration_ms=result.get("duration_ms", 0.0),
            )
        except httpx.HTTPError as e:
            logger.error("Whisper transcription failed", {"error": str(e)})
            raise RuntimeError(f"STT service unavailable: {e}")

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False
