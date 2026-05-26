import io
import asyncio
import numpy as np
import soundfile as sf
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from src.hybrid_audio import HybridAudioPipeline
from src.logging import get_logger

logger = get_logger("openai-proxy")
router = APIRouter()

KOKORO_VOICES = {"bf_isabella", "bf_emma", "af_heart", "af_bella", "af_sarah", "am_adam", "am_michael"}
OPENAI_VOICE_MAP = {
    "alloy": "bf_isabella",
    "echo": "bf_isabella",
    "fable": "bf_isabella",
    "nova": "bf_isabella",
    "onyx": "bf_isabella",
    "shimmer": "bf_isabella",
}

_pipeline: HybridAudioPipeline | None = None
_phrase_cache: dict[tuple[str, str], bytes] = {}


def _resolve_voice(voice: str) -> str:
    if voice in KOKORO_VOICES:
        return voice
    return OPENAI_VOICE_MAP.get(voice, "bf_isabella")


def get_pipeline() -> HybridAudioPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = HybridAudioPipeline()
    return _pipeline


async def warmup_cache():
    """Pre-generate common short phrases so they return instantly at runtime."""
    pipeline = get_pipeline()
    phrases = ["mm-hmm", "yeah", "okay", "sure", "right", "uh-huh", "mhm", "hey", "hmm", "ah"]
    voice = "bf_isabella"
    count = 0
    for phrase in phrases:
        try:
            wav = await pipeline.tts.synthesize_raw(phrase, voice=voice)
            if len(wav) > 44:
                _phrase_cache[(phrase, voice)] = wav
                count += 1
        except Exception as e:
            logger.warn("Cache warmup failed", {"phrase": phrase, "error": str(e)})
    logger.info("Phrase cache warmed", {"count": count})


class OpenAITTSSpeechRequest(BaseModel):
    model: str = "tts-1"
    input: str
    voice: str = "bf_isabella"
    response_format: str = "wav"
    speed: float = 1.0


@router.post("/v1/audio/speech")
async def openai_speech(req: OpenAITTSSpeechRequest):
    pipeline = get_pipeline()
    voice = _resolve_voice(req.voice)

    cleaned, actions = pipeline._extract_actions(req.input)

    sr = 24000
    all_pcm: list[np.ndarray] = []

    for action in actions:
        reaction_file = pipeline.reactions.get_reaction_for_action(action)
        if reaction_file:
            try:
                data, _ = sf.read(reaction_file, dtype="int16")
                all_pcm.append(data)
            except Exception:
                pass

    if cleaned.strip():
        chunks = pipeline._split_sentences(cleaned.strip())

        async def gen_chunk(chunk: str) -> np.ndarray | None:
            cache_key = (chunk.strip().lower(), voice)
            cached = _phrase_cache.get(cache_key)
            if cached:
                wav_bytes = cached
            else:
                wav_bytes = await pipeline.tts.synthesize_raw(chunk, voice=voice)
            if len(wav_bytes) > 44:
                return np.frombuffer(wav_bytes[44:], dtype=np.int16)
            return None

        results = await asyncio.gather(*[gen_chunk(c) for c in chunks], return_exceptions=True)
        for r in results:
            if isinstance(r, np.ndarray):
                all_pcm.append(r)
            elif isinstance(r, Exception):
                logger.error("TTS chunk failed", {"error": str(r)})

    if not all_pcm:
        raise HTTPException(status_code=500, detail="No audio generated")

    combined = np.concatenate(all_pcm)
    buf = io.BytesIO()
    sf.write(buf, combined, sr, format="wav")

    return Response(content=buf.getvalue(), media_type="audio/wav")
