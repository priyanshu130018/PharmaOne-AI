import logging
import sys

from app.core.config import get_settings


def configure_logging() -> None:
    """Configure root logging.

    Log level is derived from ENVIRONMENT (env-driven, no magic literals in
    call sites). Output goes to stdout so container runtimes can collect it.
    """
    settings = get_settings()
    level = logging.DEBUG if settings.ENVIRONMENT == "test" else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
