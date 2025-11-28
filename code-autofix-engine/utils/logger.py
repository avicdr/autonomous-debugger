# utils/logger.py
"""
Centralized logging utilities for the repair system.
"""

import logging
import sys


def setup_logger(name: str = "repair_system", level=logging.DEBUG):
    """Sets up a global logger with console output."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s",
            "%Y-%m-%d %H:%M:%S"
        )
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger


def log_step(message: str):
    """Standard log line for iteration steps."""
    logger = logging.getLogger("repair_system")
    if not logger.handlers:
        setup_logger()
    logger.info(message)


def log_header(title: str = ""):
    """
    Prints a visually distinct header section in logs.
    Example:
        log_header("=== Starting Repair Loop ===")
    """
    logger = logging.getLogger("repair_system")
    if not logger.handlers:
        setup_logger()

    bar = "=" * len(title) if title else "=" * 50
    logger.info(f"\n{bar}")
    if title:
        logger.info(title)
        logger.info(bar)
    else:
        logger.info(bar)
