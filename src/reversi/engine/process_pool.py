from __future__ import annotations

import atexit
import multiprocessing
import threading
from concurrent.futures import ProcessPoolExecutor
from typing import Optional

_executor: Optional[ProcessPoolExecutor] = None
_executor_lock = threading.Lock()


def _create_executor() -> ProcessPoolExecutor:
    # Use 'spawn' context for safety with Flet/GUI libraries and to ensure clean worker state
    try:
        ctx = multiprocessing.get_context("spawn")
        return ProcessPoolExecutor(max_workers=2, mp_context=ctx)
    except Exception:
        # Fallback if spawn is not available or fails
        return ProcessPoolExecutor(max_workers=2)


def get_executor() -> ProcessPoolExecutor:
    """Return a shared process pool dedicated to Rust analysis jobs."""
    global _executor
    if _executor is None:
        with _executor_lock:
            _executor = _create_executor()
    return _executor


def shutdown_executor(wait: bool = False):
    """Shut down the shared executor to prevent zombie worker processes."""
    global _executor
    with _executor_lock:
        if _executor is not None:
            _executor.shutdown(wait=wait)
            _executor = None


atexit.register(shutdown_executor)
