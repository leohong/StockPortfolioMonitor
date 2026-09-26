from __future__ import annotations

from statistics import median
from time import perf_counter


def benchmark(name, operation, repeats=3) -> dict:
    durations = []
    result = None
    for _ in range(repeats):
        started = perf_counter()
        result = operation()
        durations.append((perf_counter() - started) * 1000)
    return {"operation": name, "repeats": repeats, "median_ms": median(durations),
            "max_ms": max(durations), "result_size": len(result) if hasattr(result, "__len__") else None}
