import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional

from src.stt import WhisperClient
from src.tts import KokoroClient
from src.hybrid_audio import HybridAudioPipeline
from src.reaction_sounds import ReactionSoundEngine
from src.logging import get_logger, log_request

logger = get_logger("audio-route")

router = APIRouter()


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    speed: Optional[float] = None
    pitch: Optional[float] = None
    volume: Optional[float] = None


class TranscriptionResponse(BaseModel):
    text: str
    confidence: float
    language: str
    duration_ms: float


class TTSSResponse(BaseModel):
    duration_ms: float
    sample_rate: int
    format: str


@router.post("/stt", response_model=TranscriptionResponse)
async def transcribe_audio(file: UploadFile = File(...), language: Optional[str] = None):
    request_id = str(uuid.uuid4())
    log_request(logger, request_id, endpoint="audio/stt", method="POST")

    try:
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            client = WhisperClient()
            result = await client.transcribe_file(tmp_path, language=language)

            return TranscriptionResponse(
                text=result.text,
                confidence=result.confidence,
                language=result.language,
                duration_ms=result.duration_ms,
            )
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        logger.error("STT failed", {"request_id": request_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tts", response_model=TTSSResponse)
async def synthesize_speech(request: TTSRequest):
    request_id = str(uuid.uuid4())
    log_request(logger, request_id, endpoint="audio/tts", method="POST")

    try:
        client = KokoroClient()
        result = await client.synthesize(
            text=request.text,
            voice=request.voice,
            speed=request.speed,
            pitch=request.pitch,
            volume=request.volume,
        )

        return TTSSResponse(
            duration_ms=result.duration_ms,
            sample_rate=result.sample_rate,
            format=result.format,
        )
    except Exception as e:
        logger.error("TTS failed", {"request_id": request_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hybrid")
async def process_hybrid_audio(text: str, voice: Optional[str] = None):
    request_id = str(uuid.uuid4())
    log_request(logger, request_id, endpoint="audio/hybrid", method="POST")

    try:
        pipeline = HybridAudioPipeline()
        outputs = await pipeline.process_text(text, voice=voice)

        return {
            "outputs": [
                {
                    "type": "tts" if o.tts_result else "reaction",
                    "duration_ms": o.total_duration_ms or 500,
                    "file": o.reaction_file,
                }
                for o in outputs
            ],
            "total_duration_ms": sum(o.total_duration_ms or 500 for o in outputs),
        }
    except Exception as e:
        logger.error("Hybrid audio failed", {"request_id": request_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interrupt")
async def interrupt_audio():
    request_id = str(uuid.uuid4())
    log_request(logger, request_id, endpoint="audio/interrupt", method="POST")

    try:
        pipeline = HybridAudioPipeline()
        await pipeline.interrupt()
        return {"interrupted": True}
    except Exception as e:
        logger.error("Interrupt failed", {"request_id": request_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reactions")
async def list_reactions():
    engine = ReactionSoundEngine()
    return {"reactions": engine.get_all_reactions()}


@router.get("/health")
async def audio_health():
    pipeline = HybridAudioPipeline()
    health = await pipeline.health_check()
    return {"status": "ok" if all(health.values()) else "degraded", "services": health}
