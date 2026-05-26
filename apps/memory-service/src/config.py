from pathlib import Path

from pydantic_settings import BaseSettings
from functools import lru_cache

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_memory_model: str = "mistral-nemo:12b"

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""
    qdrant_collection: str = "lira_memories"

    st_base_url: str = "http://localhost:8001"
    st_api_key: str = ""

    service_port: int = 8003
    cors_origins: list[str] = ["http://localhost:8001", "http://localhost:3000"]

    log_level: str = "info"

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
