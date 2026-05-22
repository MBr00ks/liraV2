from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.config import Settings
from src.logging import get_logger

logger = get_logger("orchestrator")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Lira V2 Orchestrator starting")
    yield
    logger.info("Lira V2 Orchestrator shutting down")


def create_app() -> FastAPI:
    settings = Settings()

    app = FastAPI(
        title="Lira V2 Orchestrator API",
        description="Persistent orchestrated AI companion system",
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

    from src.routes.chat import router as chat_router
    from src.routes.memory import router as memory_router
    from src.routes.emotion import router as emotion_router
    from src.routes.openai_compat import router as openai_compat_router

    app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
    app.include_router(memory_router, prefix="/api/memory", tags=["memory"])
    app.include_router(emotion_router, prefix="/api/emotion", tags=["emotion"])
    app.include_router(openai_compat_router, prefix="/v1", tags=["openai-compatible"])

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "service": "lira-orchestrator", "version": "0.1.0"}

    return app


app = create_app()
