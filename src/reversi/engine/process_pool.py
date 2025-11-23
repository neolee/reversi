import multiprocessing
from concurrent.futures import ProcessPoolExecutor

_executor = None

def get_executor():
    global _executor
    if _executor is None:
        # Use 'spawn' context for safety with Flet/GUI libraries and to ensure clean worker state
        try:
            ctx = multiprocessing.get_context("spawn")
            _executor = ProcessPoolExecutor(max_workers=2, mp_context=ctx)
        except Exception:
            # Fallback if spawn is not available or fails
            _executor = ProcessPoolExecutor(max_workers=2)
    return _executor
