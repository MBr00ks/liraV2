from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral-nemo-fixed"
    kokoro_tts_url: str = "http://localhost:19008/v1/audio/speech"
    whisper_url: str = "http://localhost:19002/transcribe"
    lore_path: str = ""
    host: str = "127.0.0.1"
    port: int = 8001
    comfyui_base_url: str = "http://localhost:8188"
    comfyui_workflow_path: str = ""
    comfyui_output_dir: str = ""
    max_history: int = 20

    model_config = {"env_prefix": "LIRA_", "env_file": "../../../.env", "extra": "ignore"}


settings = Settings()
