import structlog
import logging
import os
from datetime import datetime, timezone


def get_logger(subsystem: str):
    """
    Create a structured logger for a Lira V2 subsystem.

    Logs: subsystem, request_id, model, tool, latency, failure reason, fallback path.
    Avoids: private intimate text, raw camera data, sensitive relationship memory, secrets.
    """
    log_level_str = os.getenv("LOG_LEVEL", "info").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger(subsystem=subsystem)


def log_request(logger, request_id: str, **kwargs):
    """Log a request with standard fields."""
    logger.info(
        "request",
        request_id=request_id,
        **kwargs,
    )


def log_latency(logger, request_id: str, model: str, latency_ms: float, **kwargs):
    """Log model call latency."""
    logger.info(
        "latency",
        request_id=request_id,
        model=model,
        latency_ms=round(latency_ms, 2),
        **kwargs,
    )


def log_failure(logger, request_id: str, reason: str, fallback_path: str | None = None, **kwargs):
    """Log a failure with optional fallback."""
    logger.error(
        "failure",
        request_id=request_id,
        reason=reason,
        fallback_path=fallback_path,
        **kwargs,
    )


def log_fallback(logger, request_id: str, from_path: str, to_path: str, **kwargs):
    """Log a fallback activation."""
    logger.warning(
        "fallback",
        request_id=request_id,
        from_path=from_path,
        to_path=to_path,
        **kwargs,
    )


def log_tool_call(logger, request_id: str, tool: str, **kwargs):
    """Log a tool invocation."""
    logger.info(
        "tool_call",
        request_id=request_id,
        tool=tool,
        **kwargs,
    )
