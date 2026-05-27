import io
import asyncio
import random
import numpy as np
import soundfile as sf
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from src.hybrid_audio import HybridAudioPipeline
from src.breath_sounds import BreathSoundEngine
from src.audio_utils import resample_to_target
from src.log import get_logger

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

PAUSE_RANGES: dict[str, tuple[float, float]] = {
    ",": (0.120, 0.200),
    ";": (0.120, 0.200),
    ":": (0.120, 0.200),
    ".": (0.220, 0.350),
    "!": (0.250, 0.400),
    "?": (0.250, 0.400),
    "...": (0.450, 0.700),
}

_pipeline: HybridAudioPipeline | None = None
_breath_engine: BreathSoundEngine | None = None
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


def get_breath_engine() -> BreathSoundEngine:
    global _breath_engine
    if _breath_engine is None:
        _breath_engine = BreathSoundEngine()
    return _breath_engine


def _trailing_punctuation(text: str) -> str:
    text = text.rstrip()
    if text.endswith("..."):
        return "..."
    if text and text[-1] in ".,!?;:":
        return text[-1]
    return ""


def _pause_samples(text: str, sr: int) -> np.ndarray:
    punct = _trailing_punctuation(text)
    if punct in PAUSE_RANGES:
        lo, hi = PAUSE_RANGES[punct]
        duration = random.uniform(lo, hi)
    else:
        duration = random.uniform(0.120, 0.200)
    n = int(sr * duration)
    return np.zeros(n, dtype=np.int16)


async def warmup_cache():
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
    sr = 48000
    all_pcm: list[np.ndarray] = []

    chunks = pipeline._split_with_actions(req.input)

    async def gen_chunk(chunk_text: str, voice: str) -> np.ndarray | None:
        cache_key = (chunk_text.strip().lower(), voice)
        cached = _phrase_cache.get(cache_key)
        if cached:
            wav_bytes = cached
        else:
            wav_bytes = await pipeline.tts.synthesize_raw(chunk_text, voice=voice)
        if len(wav_bytes) > 44:
            pcm = np.frombuffer(wav_bytes[44:], dtype=np.int16)
            return resample_to_target(pcm, 24000, 48000)
        return None

    tts_inputs: list[tuple[int, str]] = []
    chunk_reactions: dict[int, list[np.ndarray]] = {}

    for idx, (cleaned, actions) in enumerate(chunks):
        chunk_reactions[idx] = []
        for action in actions:
            reaction_data = pipeline.reactions.get_reaction_for_action(action)
            if reaction_data is not None:
                vol = random.uniform(0.85, 1.0)
                data = reaction_data.astype(np.float32) * vol
                chunk_reactions[idx].append(np.clip(data, -32768, 32767).astype(np.int16))
        if cleaned:
            tts_inputs.append((idx, cleaned))

    if tts_inputs:
        results = await asyncio.gather(*[gen_chunk(txt, voice) for _, txt in tts_inputs], return_exceptions=True)

        for (idx, _), r in zip(tts_inputs, results):
            if isinstance(r, Exception):
                logger.error("TTS chunk failed", {"error": str(r)})
                continue
            if not isinstance(r, np.ndarray):
                continue

            for rd in chunk_reactions.get(idx, []):
                all_pcm.append(rd)

            if idx > 0:
                pause = _pause_samples(chunks[idx - 1][0], sr)
                all_pcm.append(pause)

                breath_engine = get_breath_engine()
                should_add, breath_cat = breath_engine.should_add_breath(
                    idx, len(chunks), chunk_text=chunks[idx][0], full_text=req.input
                )
                if should_add and breath_cat:
                    breath_data = breath_engine.get_breath(breath_cat, volume_scale=0.5)
                    if breath_data is not None:
                        all_pcm.append(breath_data)

            all_pcm.append(r)

    if not all_pcm:
        raise HTTPException(status_code=500, detail="No audio generated")

    combined = np.concatenate(all_pcm)
    buf = io.BytesIO()
    sf.write(buf, combined, sr, format="wav")

    return Response(content=buf.getvalue(), media_type="audio/wav")
