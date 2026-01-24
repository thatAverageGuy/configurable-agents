"""Logging configuration for configurable-agents"""

import logging
import os
import sys
from typing import Optional


def setup_logging(level: Optional[str] = None) -> None:
    """
    Configure logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
               If None, uses LOG_LEVEL env var or defaults to INFO.
    """
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")

    # Convert string to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    # Create logger for this package
    logger = logging.getLogger("configurable_agents")
    logger.setLevel(numeric_level)

    logger.debug(f"Logging configured at {level} level")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"configurable_agents.{name}")
