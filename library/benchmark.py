import threading
import time
from pathlib import Path

"""
This is a benchmarking function.
It measures time since the last benchmark() call in the same thread and function.

It'll be placed in all critical functions for optimization purposes.
"""

# Store state per thread AND per function
_benchmark_state = threading.local()

if __debug__:
    def _get_function_state():
        """Get or create state for the current function in this thread."""
        import inspect
        
        # Get the caller's function name and file name
        frame = inspect.currentframe()
        try:
            # Go up two frames: _get_function_state -> benchmark -> caller
            caller_frame = frame.f_back.f_back
            function_name = caller_frame.f_code.co_name
            filename = Path(caller_frame.f_code.co_filename).name
            # Create a unique key combining file and function name
            # (in case the same function name appears in different files)
            key = f"{filename}::{function_name}"
        finally:
            del frame
        
        # Initialize thread-local storage if needed
        if not hasattr(_benchmark_state, "functions"):
            _benchmark_state.functions = {}
        
        # Get or create state for this function
        if key not in _benchmark_state.functions:
            _benchmark_state.functions[key] = {
                "last_time": None,
                "count": 0,
                "total_time": 0.0,
                "function": function_name,
                "file": filename
            }
        
        return _benchmark_state.functions[key]
    
    def benchmark(label: str = ""):
        """
        Logs time elapsed since the last benchmark() call in the same thread and function.
        First call in each function initializes the timer.
        """
        now = time.perf_counter()
        func_state = _get_function_state()
        
        # Get the caller's info for display purposes
        import inspect
        frame = inspect.currentframe()
        try:
            caller_frame = frame.f_back
            function_name = caller_frame.f_code.co_name
            filename = Path(caller_frame.f_code.co_filename).name
        finally:
            del frame
        
        last = func_state["last_time"]
        func_state["last_time"] = now
        func_state["count"] += 1
        
        if last is None:
            print(f"[BENCHMARK] {label} -> start (function: {function_name} in {filename})")
        else:
            delta_ms = (now - last) * 1000
            func_state["total_time"] += delta_ms
            print(f"[BENCHMARK -> {function_name} in {filename}] {label} -> {delta_ms:.2f} ms")
    
    def print_benchmark_summary():
        """Print summary statistics for all functions."""
        if not hasattr(_benchmark_state, "functions"):
            print("[BENCHMARK] No benchmarks recorded.")
            return
        
        print("\n" + "="*60)
        print("BENCHMARK SUMMARY (per function)")
        print("="*60)
        for key, stats in sorted(_benchmark_state.functions.items()):
            func_name = stats["function"]
            filename = stats["file"]
            count = stats["count"]
            total = stats["total_time"]
            avg = total / count if count > 0 else 0
            print(f"{func_name} ({filename}):")
            print(f"  Calls: {count}")
            print(f"  Total: {total:.2f} ms")
            print(f"  Avg:   {avg:.2f} ms")
        print("="*60)
else:
    # No-op functions when optimized
    def benchmark(label: str = ""):
        pass
    
    def print_benchmark_summary():
        pass