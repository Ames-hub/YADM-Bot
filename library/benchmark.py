import threading
import time

"""
This is a benchmarking function. (obviously)
It measures how long its been since the last benchmark() was called.
"""

_benchmark_state = threading.local()

def benchmark(label: str = ""):
    """
    Logs time elapsed since the last benchmark() call in the same thread.
    First call initializes the timer.
    """
    now = time.perf_counter()

    last = getattr(_benchmark_state, "last_time", None)
    _benchmark_state.last_time = now

    if last is None:
        print(f"[BENCHMARK] {label} -> start")
    else:
        delta_ms = (now - last) * 1000
        print(f"[BENCHMARK] {label} -> {delta_ms:.2f} ms")
