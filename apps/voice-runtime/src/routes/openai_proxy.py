import io
import os
import asyncio
import random
from datetime import datetime
import numpy as np
import soundfile as sf
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from src.hybrid_audio import HybridAudioPipeline
from src.prosody import ProsodyProfile, classify_chunk, jitter_pause, MODE_SPEEDS, PAUSE_HINT_PAUSE
from src.phonetics import apply_phonetics, normalize_for_tts, extract_pause
from src.audio_utils import resample_to_target
from src.log import get_logger
from src.config import get_settings
from src.tts import KokoroClient
from src.tts_bark import BarkClient

logger = get_logger("openai-proxy")
router = APIRouter()

KOKORO_VOICES = {"bf_isabella", "bf_emma"}
OPENAI_VOICE_MAP = {
    "alloy": "bf_isabella",
    "echo": "bf_isabella",
    "fable": "bf_isabella",
    "nova": "bf_isabella",
    "onyx": "bf_isabella",
    "shimmer": "bf_isabella",
}

SR = 48000
FADE_IN_SAMPLES = 144   # ~3ms at 48kHz — soft onset without audible delay
CROSSFADE_SAMPLES = 240  # ~5ms at 48kHz — smooth seam between adjacent chunks
COMMA_PAUSE_SAMPLES = 2880  # ~60ms at 48kHz — micro-pause at commas

_pipeline: HybridAudioPipeline | None = None
_phrase_cache: dict[tuple[str, str], bytes] = {}
_recording_buffer: list[np.ndarray] | None = None
_tts_client: KokoroClient | BarkClient | None = None
_active_backend: str | None = None  # override for config


def _resolve_voice(voice: str) -> str:
    if voice in KOKORO_VOICES:
        return voice
    return OPENAI_VOICE_MAP.get(voice, "bf_isabella")


def get_pipeline() -> HybridAudioPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = HybridAudioPipeline()
    return _pipeline


def get_tts_client() -> KokoroClient | BarkClient:
    global _tts_client
    if _tts_client is None:
        settings = get_settings()
        backend = _active_backend or settings.tts_backend
        if backend == "bark":
            _tts_client = BarkClient()
        else:
            _tts_client = KokoroClient()
    return _tts_client


def _fade_in(data: np.ndarray) -> np.ndarray:
    """Apply a short fade-in to the start of a chunk for soft onset."""
    result = data.astype(np.float32)
    n = len(result)
    f = min(FADE_IN_SAMPLES, n)
    if f > 0:
        result[:f] *= np.linspace(0, 1, f)
    return result.astype(np.int16)


async def warmup_cache():
    settings = get_settings()
    backend = _active_backend or settings.tts_backend
    if backend == "bark":
        logger.info("Skipping phrase cache warmup (Bark too slow on CPU)")
        return
    tts = get_tts_client()
    phrases = ["mm-hmm", "yeah", "okay", "sure", "right", "uh-huh", "mhm", "hey", "hmm", "ah"]
    voice = "bf_isabella"
    speed = 1.0
    count = 0
    for phrase in phrases:
        try:
            wav = await tts.synthesize_raw(phrase, voice=voice, speed=speed)
            if len(wav) > 44:
                _phrase_cache[(phrase, voice, speed)] = wav
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
    mode: str = ""  # assistant | companion | observer — sets base prosody


@router.post("/v1/audio/speech")
async def openai_speech(req: OpenAITTSSpeechRequest):
    import time
    t_start = time.monotonic()
    cache_hits = 0
    cache_misses = 0
    pipeline = get_pipeline()
    mode_speed = MODE_SPEEDS.get(req.mode, 1.0)
    voice = _resolve_voice(req.voice)
    sr = 48000
    all_pcm: list[np.ndarray] = []

    chunks = pipeline._split_with_actions(req.input)

    async def gen_chunk(chunk_text: str, voice: str, speed: float = 1.0) -> np.ndarray | None:
        nonlocal cache_hits, cache_misses
        cache_key = (chunk_text.strip().lower(), voice, speed)
        cached = _phrase_cache.get(cache_key)
        if cached:
            cache_hits += 1
            wav_bytes = cached
        else:
            cache_misses += 1
            tts = get_tts_client()
            wav_bytes = await tts.synthesize_raw(chunk_text, voice=voice, speed=speed)
        if len(wav_bytes) > 44:
            pcm = np.frombuffer(wav_bytes[44:], dtype=np.int16)
            return resample_to_target(pcm, 24000, 48000)
        return None

    tts_inputs: list[tuple[int, str, ProsodyProfile]] = []
    chunk_pauses: list[float] = []  # extra silence in seconds for [pause:X.Xs] tokens
    chunk_reactions: dict[int, list[np.ndarray]] = {}

    for idx, (cleaned, actions) in enumerate(chunks):
        chunk_reactions[idx] = []
        had_reaction = False
        for action in actions:
            reaction_data = pipeline.reactions.get_reaction_for_action(action)
            if reaction_data is not None:
                vol = random.uniform(0.85, 1.0)
                data = reaction_data.astype(np.float32) * vol
                chunk_reactions[idx].append(np.clip(data, -32768, 32767).astype(np.int16))
                had_reaction = True
        if not cleaned and actions and not had_reaction:
            continue  # skip unmatched standalone actions — don't speak them
        if cleaned:
            cleaned = normalize_for_tts(cleaned)
            cleaned, pause_sec = extract_pause(cleaned)
            cleaned = apply_phonetics(cleaned)
            profile = classify_chunk(cleaned)
            # Apply mode-based speed modifier
            if mode_speed != 1.0:
                profile.speed = round(profile.speed * mode_speed, 3)
            # Pause hint: ellipsis or em dash triggers a longer pause
            has_pause_hint = any(h in cleaned for h in ("...", "\u2014"))
            if has_pause_hint:
                profile = ProsodyProfile(
                    name=profile.name,
                    speed=profile.speed,
                    pause_range=(profile.pause_range[0] + 0.3, profile.pause_range[1] + 0.3),
                    volume_scale=profile.volume_scale,
                    allow_breath=profile.allow_breath,
                    allow_reaction=profile.allow_reaction,
                    pause_jitter=profile.pause_jitter,
                )
            tts_inputs.append((idx, cleaned, profile))
            chunk_pauses.append(pause_sec or 0.0)

    if tts_inputs:
        results = await asyncio.gather(
            *[gen_chunk(txt, voice, prof.speed) for _, txt, prof in tts_inputs],
            return_exceptions=True,
        )

        prev_profile: ProsodyProfile | None = None
        prev_speed: float = 1.0

        for seq_idx, ((idx, _, profile), r) in enumerate(zip(tts_inputs, results)):
            if isinstance(r, Exception):
                logger.error("TTS chunk failed", {"error": str(r)})
                continue
            if not isinstance(r, np.ndarray):
                continue

            if profile.allow_reaction:
                for rd in chunk_reactions.get(idx, []):
                    all_pcm.append(rd)

            # Speed smoothing — blend toward previous speed to avoid jarring jumps
            smoothed_speed = profile.speed
            if prev_profile is not None:
                diff = abs(smoothed_speed - prev_speed)
                if diff > 0.03:
                    smoothed_speed = prev_speed + (smoothed_speed - prev_speed) * 0.5
                    if abs(smoothed_speed - profile.speed) > 0.01:
                        chunk_text = tts_inputs[seq_idx][1]
                        new_r = await gen_chunk(chunk_text, voice, smoothed_speed)
                        if isinstance(new_r, np.ndarray):
                            r = new_r

            prev_speed = smoothed_speed

            if profile.volume_scale != 1.0:
                r = (r.astype(np.float32) * profile.volume_scale).clip(-32768, 32767).astype(np.int16)

            if prev_profile is not None and all_pcm:
                pause_sec = jitter_pause(prev_profile)
                pause_samples = int(pause_sec * sr)

                overlap = min(CROSSFADE_SAMPLES, len(all_pcm[-1]), len(r))

                if overlap > 0:
                    # Crossfade tail of previous chunk with head of this chunk
                    prev_tail = all_pcm[-1][-overlap:].astype(np.float32)
                    prev_tail *= np.linspace(1, 0, overlap)

                    cur_head = r[:overlap].astype(np.float32)
                    cur_head *= np.linspace(0, 1, overlap)

                    crossfade = np.clip(prev_tail + cur_head, -32768, 32767).astype(np.int16)

                    # Replace tail of previous segment with crossfade
                    all_pcm[-1] = np.concatenate([all_pcm[-1][:-overlap], crossfade])

                    # Remaining pause after overlap consumed by crossfade
                    remaining_pause = max(0, pause_samples - overlap)
                    if remaining_pause > 0:
                        all_pcm.append(np.zeros(remaining_pause, dtype=np.int16))
                else:
                    if pause_samples > 0:
                        all_pcm.append(np.zeros(pause_samples, dtype=np.int16))

                # Fade in the portion beyond the crossfade head
                body = r[overlap:] if overlap > 0 else r
                if len(body) > 0:
                    all_pcm.append(_fade_in(body))
            else:
                # First chunk: just fade in
                all_pcm.append(_fade_in(r))

            prev_profile = profile

            # Extra pause from [pause:X.Xs] token
            extra_pause = chunk_pauses[seq_idx] if seq_idx < len(chunk_pauses) else 0.0
            if extra_pause > 0:
                extra_samples = int(extra_pause * sr)
                if extra_samples > 0:
                    all_pcm.append(np.zeros(extra_samples, dtype=np.int16))

    if not all_pcm:
        raise HTTPException(status_code=500, detail="No audio generated")

    combined = np.concatenate(all_pcm)
    buf = io.BytesIO()
    sf.write(buf, combined, sr, format="wav")
    wav_bytes = buf.getvalue()

    t_elapsed = round((time.monotonic() - t_start) * 1000)
    duration_s = round(len(combined) / sr, 1)
    logger.info("tts_request",
        mode=req.mode or "default",
        chunks=len(tts_inputs) if tts_inputs else 0,
        cache_hits=cache_hits,
        cache_misses=cache_misses,
        duration_s=duration_s,
        latency_ms=t_elapsed,
        bytes=len(wav_bytes))

    global _recording_buffer
    if _recording_buffer is not None:
        if _recording_buffer:
            _recording_buffer.append(np.zeros(RECORD_GAP_SAMPLES, dtype=np.int16))
        _recording_buffer.append(combined)

    return Response(content=wav_bytes, media_type="audio/wav")


@router.get("/tts-backend")
async def get_tts_backend():
    settings = get_settings()
    return {"backend": _active_backend or settings.tts_backend}


@router.post("/tts-backend")
async def set_tts_backend(backend: str):
    global _tts_client, _active_backend
    if backend not in ("kokoro", "bark"):
        raise HTTPException(status_code=400, detail="Backend must be 'kokoro' or 'bark'")
    _active_backend = backend
    _tts_client = None  # reset so next call picks the new backend
    logger.info("TTS backend switched", {"backend": backend})
    return {"backend": backend}


@router.post("/record/start")
async def record_start():
    global _recording_buffer
    _recording_buffer = []
    return {"status": "recording"}


@router.post("/record/stop")
async def record_stop():
    global _recording_buffer
    if _recording_buffer is None:
        raise HTTPException(status_code=400, detail="Not recording")
    if not _recording_buffer:
        _recording_buffer = None
        raise HTTPException(status_code=400, detail="No audio recorded")
    combined = np.concatenate(_recording_buffer)
    _recording_buffer = None
    buf = io.BytesIO()
    sf.write(buf, combined, 48000, format="wav")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    path = os.path.join(DESKTOP, f"lira-conversation-{ts}.wav")
    with open(path, "wb") as f:
        f.write(buf.getvalue())
    return {"status": "saved", "path": path}
