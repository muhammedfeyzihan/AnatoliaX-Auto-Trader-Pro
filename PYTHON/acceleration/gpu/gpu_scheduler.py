"""
gpu/gpu_scheduler.py — GPU gorev zamanlayicisi (oncelikli kuyruk + akis yonetimi)
"""
import heapq
from dataclasses import dataclass, field
from typing import Callable, Dict, List


@dataclass(order=True)
class GPUTask:
    priority: int
    seq: int = field(compare=True)
    func: Callable = field(compare=False)
    args: tuple = field(compare=False)
    kwargs: dict = field(compare=False)
    stream_name: str = field(default="normal", compare=False)


class GPUTaskScheduler:
    """
    GPU gorev zamanlayicisi.

    Ozellikler:
    - Oncelikli kuyruk (kucuk sayi = yuksek oncelik)
    - Akis atama: normal, high, critical
    - Olay tabanli senkronizasyon

    Kullanim:
        scheduler = GPUTaskScheduler(cuda_context)
        scheduler.submit(priority=1, func=kernel, args=(a, b), stream="high")
    """

    def __init__(self, cuda_context):
        self._ctx = cuda_context
        self._queue: List[GPUTask] = []
        self._counter = 0

    def submit(self, priority: int, func: Callable, args: tuple = (), kwargs: dict = None,
               stream: str = "normal") -> None:
        self._counter += 1
        task = GPUTask(priority, self._counter, func, args, kwargs or {}, stream)
        heapq.heappush(self._queue, task)

    def run_next(self) -> None:
        if not self._queue:
            return
        task = heapq.heappop(self._queue)
        stream = self._ctx.get_stream(task.stream_name)
        if stream:
            with stream:
                task.func(*task.args, **task.kwargs)
        else:
            task.func(*task.args, **task.kwargs)
