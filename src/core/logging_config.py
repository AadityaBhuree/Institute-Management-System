"""Institute Management System - Structured Logging Configuration."""

import logging
import sys
from typing import Optional


def setup_logging(level: Optional[int] = None) -> logging.Logger:
    """Configure standardized application logger with structured formatting."""
    log_level = level if level is not None else logging.INFO

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger("ims")
    root_logger.setLevel(log_level)

    # Avoid adding duplicate handlers on multiple reloads
    if not root_logger.handlers:
        root_logger.addHandler(handler)

    return root_logger


logger = logging.getLogger("ims")
