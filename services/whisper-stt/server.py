import tempfile
import os
import numpy as np
import soundfile as sf
from fastapi import FastAPI, UploadFile, File, HTTPException
import whisper

app = FastAPI(title="Whisper STT")
_model = None


def _load():
    global _model
    if _model is not None:
        return _model
    _model = whisper.load_model("tiny.en")
    return _model


@app.get("/health")
async def health():
    return {"status": "ok", "model": "tiny.en"}


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    model = _load()
    try:
        audio_bytes = await file.read()
        # Decode with soundfile (no ffmpeg needed)
        audio, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
        # Convert to mono if stereo
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        # Resample to 16kHz if needed
        if sr != 16000:
            import scipy.signal
            ratio = 16000 / sr
            audio = scipy.signal.resample(audio, int(len(audio) * ratio))
        # Pad/trim to 30 seconds
        audio = whisper.pad_or_trim(audio)
        # Make log-Mel spectrogram
        mel = whisper.log_mel_spectrogram(audio, n_mels=model.dims.n_mels).to(model.device)
        # Decode
        options = whisper.DecodingOptions(fp16=False, language="en")
        result = whisper.decode(model, mel, options)
        return {"text": result.text.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    import io
    uvicorn.run(app, host="127.0.0.1", port=19002, log_level="error")
