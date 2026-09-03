"""Structured logging configuration."""
import logging
import sys
import structlog


def configure_logging(level: str = "INFO", production: bool = False) -> None:
    logging.basicConfig(stream=sys.stdout, level=getattr(logging, level.upper(), logging.INFO), format="%(message)s")
    renderer = structlog.processors.JSONRenderer() if production else structlog.dev.ConsoleRenderer(colors=False)
    structlog.configure(
        processors=[structlog.contextvars.merge_contextvars, structlog.processors.add_log_level,
                    structlog.processors.TimeStamper(fmt="iso", utc=True), renderer],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper(), logging.INFO)),
        logger_factory=structlog.PrintLoggerFactory(), cache_logger_on_first_use=True,
    )
