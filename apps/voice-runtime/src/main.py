from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.config import Settings, get_settings
from src.logging import get_logger
from src.obs_bridge import OBSBridge


logger = get_logger("voice-runtime")

obs_bridge = OBSBridge()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Lira V2 Voice Runtime starting")
    if get_settings().obs_enabled:
        await obs_bridge.connect()

    from src.routes.openai_proxy import warmup_cache
    await warmup_cache()

    yield
    from src.routes.openai_proxy import get_pipeline
    pipeline = get_pipeline()
    await pipeline.close()
    await obs_bridge.disconnect()
    logger.info("Lira V2 Voice Runtime shutting down")


def create_app() -> FastAPI:
    settings = Settings()

    app = FastAPI(
        title="Lira V2 Voice Runtime",
        description="STT + TTS + audio mixing runtime",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from src.routes.audio import router as audio_router

    app.include_router(audio_router, prefix="/api/audio", tags=["audio"])

    from src.routes.obs import router as obs_router

    app.include_router(obs_router, prefix="/api/obs", tags=["obs"])

    from src.routes.openai_proxy import router as openai_router

    app.include_router(openai_router, tags=["openai"])

    from src.routes.ollama_proxy import router as ollama_router

    app.include_router(ollama_router, tags=["ollama"])

    @app.get("/health")
    async def health_check():
        obs_status = await obs_bridge.health_check() if get_settings().obs_enabled else None
        return {
            "status": "ok",
            "service": "lira-voice-runtime",
            "version": "0.1.0",
            "obs": {
                "enabled": get_settings().obs_enabled,
                "connected": obs_status.connected if obs_status else False,
                "tts_source_exists": obs_status.tts_source_exists if obs_status else False,
                "filters_active": obs_status.filters_active if obs_status else [],
            } if obs_status else None,
        }

    return app


app = create_app()
