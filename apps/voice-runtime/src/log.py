import logging as stdlib_logging
import structlog
from src.config import get_settings


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    settings = get_settings()
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger(name)


def log_request(logger: structlog.stdlib.BoundLogger, method: str, path: str, status: int, duration_ms: float):
    logger.info("request", method=method, path=path, status=status, duration_ms=duration_ms)
