import base64
import io
from contextlib import asynccontextmanager
from typing import Optional

import numpy as np
import soundfile as sf
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from kokoro import KPipeline
from pydantic import BaseModel

pipeline: KPipeline | None = None


class SynthesizeRequest(BaseModel):
    text: str
    voice: str = "bf_isabella"
    speed: float = 1.0
    pitch: float = 0.0
    volume: float = 0.0
    stream: bool = False


class SynthesizeResponse(BaseModel):
    audio: str
    duration_ms: float
    sample_rate: int = 24000
    format: str = "wav"


@asynccontextmanager
async def lifespan(application: FastAPI):
    global pipeline
    pipeline = KPipeline(lang_code="b")

    # Pre-warm: generate and discard a short phrase so subsequent requests
    # don't pay the cold-start cost for model loading/compilation.
    try:
        for _ in pipeline("Hello.", voice="bf_isabella", speed=1.0):
            pass
        print("Kokoro TTS warmed up.")
    except Exception as e:
        print(f"Kokoro warmup skipped ({e})")

    yield


app = FastAPI(title="Kokoro TTS", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class OpenAITTSSpeechRequest(BaseModel):
    model: str = "tts-1"
    input: str
    voice: str = "bf_isabella"
    response_format: str = "wav"
    speed: float = 1.0


def audio_to_wav_base64(audio: np.ndarray, sample_rate: int) -> str:
    buf = io.BytesIO()
    sf.write(buf, audio, sample_rate, format="wav")
    return base64.b64encode(buf.getvalue()).decode()


@app.get("/health")
async def health():
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    return {"status": "ok", "voice": "bf_isabella"}


@app.post("/synthesize")
async def synthesize(req: SynthesizeRequest):
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    if req.stream:
        return await synthesize_stream(req)

    generator = pipeline(req.text, voice=req.voice, speed=req.speed)
    all_audio: list[np.ndarray] = []
    sample_rate = 24000
    for i, (gs, ps, audio) in enumerate(generator):
        if audio is not None and len(audio) > 0:
            all_audio.append(audio)

    if not all_audio:
        raise HTTPException(status_code=500, detail="No audio generated")

    combined = np.concatenate(all_audio, axis=0)
    duration_ms = float(len(combined) / sample_rate * 1000)
    audio_b64 = audio_to_wav_base64(combined, sample_rate)

    return SynthesizeResponse(
        audio=audio_b64,
        duration_ms=duration_ms,
        sample_rate=sample_rate,
        format="wav",
    )


@app.post("/v1/audio/speech")
async def openai_speech(req: OpenAITTSSpeechRequest):
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    voice = req.voice or "bf_isabella"
    speed = req.speed or 1.0

    generator = pipeline(req.input, voice=voice, speed=speed)
    all_audio: list[np.ndarray] = []
    sample_rate = 24000
    for gs, ps, audio in generator:
        if audio is not None and len(audio) > 0:
            all_audio.append(audio)

    if not all_audio:
        raise HTTPException(status_code=500, detail="No audio generated")

    combined = np.concatenate(all_audio, axis=0)
    buf = io.BytesIO()
    sf.write(buf, combined, sample_rate, format=req.response_format)
    return Response(content=buf.getvalue(), media_type="audio/wav")


async def synthesize_stream(req: SynthesizeRequest):
    generator = pipeline(req.text, voice=req.voice, speed=req.speed)

    async def audio_stream():
        sample_rate = 24000
        for gs, ps, audio in generator:
            if audio is not None and len(audio) > 0:
                buf = io.BytesIO()
                sf.write(buf, audio, sample_rate, format="wav")
                yield buf.getvalue()

    return StreamingResponse(audio_stream(), media_type="audio/wav")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=19008)
