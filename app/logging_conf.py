"""Logging configuration helper for ArenaMate.

Configures root logging settings and provides module-level loggers.
"""

from __future__ import annotations

import logging

_CONFIGURED = False


def setup_logging(level: int = logging.INFO) -> None:
    """Initialize root logging settings idempotently.

    Args:
        level (int): The logging level to set (e.g., logging.INFO). Defaults to logging.INFO.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s]: %(message)s",
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return configured logger instance for a module.

    Args:
        name (str): The name of the logger, typically __name__.

    Returns:
        logging.Logger: The configured Logger instance.
    """
    setup_logging()
    return logging.getLogger(name)
