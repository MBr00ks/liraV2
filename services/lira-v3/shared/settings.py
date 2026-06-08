"""Canonical configuration for all Lira V2.5 services."""
from pathlib import Path
from pydantic_settings import BaseSettings

_BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # LLM
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral-nemo-fixed"
    openrouter_api_key: str = ""
    llm_fallback_threshold_ms: int = 3000

    # TTS
    kokoro_tts_url: str = "http://localhost:19008/v1/audio/speech"

    # STT
    whisper_url: str = "http://localhost:19002/transcribe"

    # Image generation
    comfyui_base_url: str = "http://localhost:8188"
    comfyui_workflow_path: str = ""
    comfyui_output_dir: str = ""
    comfyui_steps: int = 20
    comfyui_width: int = 896
    comfyui_height: int = 896
    comfyui_cfg_scale: float = 5.0
    comfyui_sampler: str = "dpmpp_2m"
    comfyui_scheduler: str = "karras"
    comfyui_model: str = "unrealvisionXLPhotoreal_realismUniversal.safetensors"
    comfyui_negative: str = "worst quality, low quality, bad anatomy, deformed, blurry, watermark, text, signature"
    lora_trigger: str = "lira_base"

    # NATS
    nats_url: str = "nats://localhost:4222"
    nats_http_port: int = 8222

    # LLM fallback
    openrouter_fallback_model: str = "mistralai/mistral-nemo"

    # Voice proxy for TTS
    voice_proxy_url: str = "http://localhost:19011/v1/audio/speech"

    # Memory
    chroma_persist_dir: str = str(_BASE_DIR / "data" / "chroma")

    # Data
    lore_path: str = str(_BASE_DIR / "data" / "lore" / "lore_data.json")
    personality_dir: str = str(_BASE_DIR / "data" / "personalities")
    log_dir: str = str(_BASE_DIR / "logs")

    # Service
    host: str = "127.0.0.1"
    port: int = 8100
    max_history: int = 20

    # Audio
    kokoro_voice: str = "bf_isabella"
    kokoro_speed: float = 1.0

    model_config = {"env_prefix": "LIRA_", "env_file": str(_BASE_DIR.parent.parent / ".env"), "extra": "ignore"}


settings = Settings()
