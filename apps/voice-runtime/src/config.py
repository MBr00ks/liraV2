from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    whisper_base_url: str = "http://localhost:19002"
    kokoro_base_url: str = "http://localhost:19008"
    kokoro_voice: str = "bf_isabella"
    kokoro_speed: float = 1.0
    kokoro_pitch: float = 0.0
    kokoro_volume: float = 0.0

    xtts_base_url: str = ""

    audio_sample_rate: int = 24000
    audio_chunk_size: int = 4096
    audio_format: str = "wav"

    reaction_sound_dir: str = "public/audio/reactions"
    breathing_sound_dir: str = "public/audio/breathing"

    log_level: str = "info"

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
