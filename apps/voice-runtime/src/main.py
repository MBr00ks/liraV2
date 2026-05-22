from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.config import Settings
from src.logging import get_logger

logger = get_logger("voice-runtime")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Lira V2 Voice Runtime starting")
    yield
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

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "service": "lira-voice-runtime", "version": "0.1.0"}

    return app


app = create_app()
