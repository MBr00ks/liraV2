import structlog
from src.config import get_settings


def get_logger(subsystem: str) -> structlog.stdlib.BoundLogger:
    settings = get_settings()
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger(subsystem=subsystem)
