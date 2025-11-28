# utils/timers.py
"""
Timing utilities for execution measurement.
"""

import time
from contextlib import contextmanager

@contextmanager
def timer(name: str = "block"):
    """Context manager to measure execution time."""
    start = time.time()
    yield
    end = time.time()
    elapsed = end - start
    print(f"[TIMER] {name}: {elapsed:.4f}s")


def measure_time(func):
    """Decorator to measure execution time of functions."""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"[TIMER] {func.__name__}: {elapsed:.4f}s")
        return result
    return wrapper
