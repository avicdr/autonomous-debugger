# utils/file_ops.py
"""
Utility functions for file operations in sandbox and repair system.
"""

import os
import logging

logger = logging.getLogger(__name__)

SANDBOX_FILE_PATH = "runtime/sandbox/user_code.py"
OUTPUT_DIR = "runtime/output"


def write_sandbox_file(code: str, path: str = None):
    """Writes user code to sandbox file."""
    path = path or SANDBOX_FILE_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    logger.debug(f"Written sandbox code to {path}")
    return path


def write_output_file(content: str, filename: str):
    """Writes content to output directory."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.debug(f"Saved {filename} to {OUTPUT_DIR}")
    return path


def read_file(path: str):
    """Read file content."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to read file {path}: {e}")
        return ""
