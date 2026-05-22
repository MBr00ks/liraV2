import structlog
import logging
import os


def get_logger(subsystem: str):
    """
    Create a structured logger for the voice runtime subsystem.
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
