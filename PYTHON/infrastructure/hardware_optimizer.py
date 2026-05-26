"""
infrastructure/hardware_optimizer.py — Hardware-Aware Optimization (Phase 2)
Module 23 from anatoliax_prompt_v6.txt

Features:
  - CPU affinity pinning via ctypes (Windows) / os.sched_setaffinity (Linux)
  - NUMA-local memory hint via mmap
  - Lock-free Michael-Scott queue stub (Python-level simulation)
  - Benchmark target: <10us for hot path
"""

import ctypes
import mmap
import os
import time
from collections import deque
from typing import Optional, Dict, List


class HardwareOptimizer:
    """
    Hardware-aware optimizations for latency-sensitive paths.
    Adds shared-memory queue, CPU pinning, NUMA hint, and hot-path benchmarking.
    """

    def __init__(self):
        self._pinned = False
        self._numa_hints: Dict[str, str] = {}
        self._shm_queues: Dict[str, "SharedMemoryQueue"] = {}

    def pin_to_core(self, core_id: int) -> bool:
        """Pin current process/thread to a specific CPU core."""
        try:
            if os.name == "nt":
                # Windows: SetThreadAffinityMask
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.GetCurrentThread()
                mask = 1 << core_id
                kernel32.SetThreadAffinityMask(handle, mask)
            else:
                os.sched_setaffinity(0, {core_id})
            self._pinned = True
            return True
        except Exception:
            return False

    def allocate_numa_local(self, size_bytes: int, node: int = 0) -> Optional[mmap.mmap]:
        """Allocate shared memory mapped region (NUMA hint)."""
        try:
            return mmap.mmap(-1, size_bytes, access=mmap.ACCESS_WRITE)
        except Exception:
            return None

    def create_shm_queue(self, name: str, size_bytes: int = 65536) -> "SharedMemoryQueue":
        """Create a named shared-memory queue backed by mmap."""
        q = SharedMemoryQueue(name, size_bytes)
        self._shm_queues[name] = q
        return q

    def benchmark_hot_path(self, fn, iterations: int = 100_000) -> Dict:
        """Measure latency of a hot path function."""
        # Warmup
        for _ in range(1000):
            fn()
        start = time.perf_counter_ns()
        for _ in range(iterations):
            fn()
        elapsed = time.perf_counter_ns() - start
        avg_ns = elapsed / iterations
        return {
            "iterations": iterations,
            "total_ns": elapsed,
            "avg_ns": avg_ns,
            "target_met": avg_ns < 10_000,  # <10us
        }

    def get_system_info(self) -> Dict:
        return {
            "cpu_count": os.cpu_count(),
            "pinned": self._pinned,
            "platform": os.name,
        }


class SharedMemoryQueue:
    """
    Shared-memory queue using mmap for cross-process communication.
    Uses a simple header (read_offset, write_offset) + circular buffer.
    """

    def __init__(self, name: str, size_bytes: int = 65536):
        self.name = name
        self.size = size_bytes
        self.header_size = 16
        try:
            self._mmap = mmap.mmap(-1, size_bytes, access=mmap.ACCESS_WRITE)
            # Initialize header: read_offset=0, write_offset=0
            self._mmap[:self.header_size] = b"\x00" * self.header_size
        except Exception:
            self._mmap = None
            self._fallback = deque()

    def _get_offsets(self):
        if self._mmap is None:
            return 0, 0
        self._mmap.seek(0)
        read_off = int.from_bytes(self._mmap.read(8), "little")
        write_off = int.from_bytes(self._mmap.read(8), "little")
        return read_off, write_off

    def _set_offsets(self, read_off: int, write_off: int):
        if self._mmap is None:
            return
        self._mmap.seek(0)
        self._mmap.write(read_off.to_bytes(8, "little"))
        self._mmap.write(write_off.to_bytes(8, "little"))

    def enqueue(self, item: bytes):
        if self._mmap is None:
            self._fallback.append(item)
            return
        read_off, write_off = self._get_offsets()
        data_len = len(item)
        total = 4 + data_len
        avail = self.size - self.header_size - ((write_off - read_off) % (self.size - self.header_size))
        if total > avail:
            raise MemoryError("SharedMemoryQueue full")
        abs_write = self.header_size + write_off
        self._mmap[abs_write:abs_write + 4] = data_len.to_bytes(4, "little")
        self._mmap[abs_write + 4:abs_write + total] = item
        new_write = (write_off + total) % (self.size - self.header_size)
        self._set_offsets(read_off, new_write)

    def dequeue(self) -> Optional[bytes]:
        if self._mmap is None:
            return self._fallback.popleft() if self._fallback else None
        read_off, write_off = self._get_offsets()
        if read_off == write_off:
            return None
        abs_read = self.header_size + read_off
        data_len = int.from_bytes(self._mmap[abs_read:abs_read + 4], "little")
        item = bytes(self._mmap[abs_read + 4:abs_read + 4 + data_len])
        new_read = (read_off + 4 + data_len) % (self.size - self.header_size)
        self._set_offsets(new_read, write_off)
        return item

    def is_empty(self) -> bool:
        if self._mmap is None:
            return len(self._fallback) == 0
        read_off, write_off = self._get_offsets()
        return read_off == write_off


class LockFreeQueue:
    """
    Simplified Michael-Scott queue simulation in Python.
    (True lock-free requires C extensions; this is the algorithmic model.)
    """

    def __init__(self, maxlen: int = 1000):
        self._buffer = deque(maxlen=maxlen)

    def enqueue(self, item):
        self._buffer.append(item)

    def dequeue(self):
        if self._buffer:
            return self._buffer.popleft()
        return None

    def is_empty(self) -> bool:
        return len(self._buffer) == 0
