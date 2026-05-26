"""
platform_optimizer.py — Cross-Platform Performance Optimizations

Provides platform detection, CPU-aware worker count calculation,
and system information for maximum speed across Windows, Linux, and macOS.

Usage:
    from common.platform_optimizer import get_optimal_workers, get_system_info
    workers = get_optimal_workers()
    info = get_system_info()
"""

import os
import platform
import sys
from typing import Dict, Optional


def is_windows() -> bool:
    return sys.platform.startswith("win")


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def is_macos() -> bool:
    return sys.platform == "darwin"


def get_cpu_count() -> int:
    """Return the number of logical CPUs, with a safe fallback."""
    try:
        return os.cpu_count() or 4
    except Exception:
        return 4


def get_optimal_workers(max_workers: Optional[int] = None, use_processes: bool = False) -> int:
    """
    Calculate the optimal number of parallel workers.

    Args:
        max_workers: Upper cap (default = CPU count).
        use_processes: If True, prefer ProcessPoolExecutor (Linux/Mac only).

    Returns:
        int: Recommended max_workers for ThreadPoolExecutor or ProcessPoolExecutor.
    """
    cpu_count = get_cpu_count()

    if max_workers is not None:
        workers = min(max_workers, cpu_count)
    else:
        workers = cpu_count

    # Windows: avoid ProcessPoolExecutor due to pickle limitations with complex objects
    if use_processes and is_windows():
        use_processes = False

    # Leave at least 1 core free for the OS / main thread
    workers = max(1, workers - 1)

    return workers


def get_executor_type(use_processes: bool = False) -> str:
    """
    Recommend executor type based on platform.

    Returns 'thread' or 'process'.
    """
    if use_processes and not is_windows():
        return "process"
    return "thread"


def get_system_info() -> Dict:
    """Return a dictionary with system/platform details."""
    return {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor() or "unknown",
        "cpu_count": get_cpu_count(),
        "python_version": sys.version,
        "optimal_workers": get_optimal_workers(),
        "recommended_executor": get_executor_type(),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_system_info(), indent=2, ensure_ascii=False))
