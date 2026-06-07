from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    whisper_base_url: str = "http://localhost:19002"
    kokoro_base_url: str = "http://localhost:19008"
    kokoro_voice: str = "bf_isabella"
    kokoro_speed: float = 1.0

    xtts_base_url: str = ""

    tts_backend: str = "kokoro"  # "kokoro" or "bark"

    bark_base_url: str = "http://localhost:19009"
    bark_voice_preset: str = "v2/en_speaker_6"
    bark_model: str = "suno/bark-small"

    audio_sample_rate: int = 24000
    audio_chunk_size: int = 4096
    audio_format: str = "wav"

    reaction_sound_dir: str = "public/audio/reactions"
    breathing_sound_dir: str = "public/audio/breathing"

    obs_host: str = "localhost"
    obs_port: int = 4455
    obs_password: str = ""
    obs_enabled: bool = False
    obs_tts_source: str = "Kokoro TTS"

    log_level: str = "info"

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
