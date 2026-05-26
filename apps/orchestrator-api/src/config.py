from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral-nemo:12b"
    ollama_memory_model: str = "mistral-nemo:12b"
    ollama_narrative_model: str = "qwen3:32b"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_keep_alive: str = "5m"

    openai_api_key: str = ""
    openai_model: str = "gpt-4.1"
    openai_memory_model: str = "gpt-4.1-nano"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "lira"
    postgres_password: str = "lira_password"
    postgres_db: str = "lira_v2"

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""

    whisper_base_url: str = "http://localhost:19002"
    kokoro_base_url: str = "http://localhost:19008"
    kokoro_voice: str = "bf_isabella"
    kokoro_speed: float = 1.0
    kokoro_pitch: float = 0.0
    kokoro_volume: float = 0.0

    comfyui_base_url: str = "http://localhost:8188"

    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""

    enable_voice: bool = True
    enable_avatar: bool = False
    enable_vision: bool = False
    enable_companion_loop: bool = False
    enable_internal_thoughts: bool = False
    debug_mode: bool = False
    safe_mode: bool = False

    log_level: str = "info"

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
