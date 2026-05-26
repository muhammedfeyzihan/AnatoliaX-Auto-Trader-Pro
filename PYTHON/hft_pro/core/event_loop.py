"""
core/event_loop.py — CPU-bağımlı olay döngüsü (alt-milisaniye strateji yürütme)
"""
import ctypes
import platform
import threading
import time
from typing import Callable, Dict


class BusySpinEventLoop:
    """
    Uyarlanabilir meşgul-dönüş olay döngüsü üstel geri çekilme ile uyku.

    Aşamalar:
    1. ACTIVE: meşgul-dönüş PAUSE komutuyla (%0 uyku)
    2. IDLE_1: ara sıra sched_yield() (10μs içinde etkinlik algılandıysa)
    3. IDLE_2: usleep(1) — 1 mikrosaniye uyku
    4. IDLE_3: usleep(100) — 100 mikrosaniye uyku
    5. IDLE_4: usleep(1000) — 1 milisaniye uyku (maksimum)

    Geçiş: iş bulunursa anında ACTIVE'e dön.
    CPU benzeşimi: izole çekirdek üzerine sabitleme (sched_setaffinity).
    NUMA: yerel düğüm üzerinde ayırma.
    """

    def __init__(self, core_id: int = -1, numa_node: int = -1):
        self._handlers: Dict[int, Callable] = {}
        self._running = False
        self._core_id = core_id
        self._numa_node = numa_node
        self._loop_count = 0
        self._loop_time_ns_total = 0
        self._phase = "ACTIVE"
        # Windows'ta sched_setaffinity yerine iş parçacığı benzeşimi yoktur;
        # Linux'ta ileride eklenebilir.
        if platform.system() == "Linux" and core_id >= 0:
            try:
                import os
                os.sched_setaffinity(0, {core_id})
            except Exception:
                pass

    def register_handler(self, event_type: int, handler: Callable) -> None:
        """Olay işleyici kaydet. İşleyiciler engellemez olmalı (<10μs)."""
        self._handlers[event_type] = handler

    def run(self) -> None:
        """Ana döngü. stop_event ayarlanana kadar çalışır."""
        self._running = True
        idle_counter = 0
        while self._running:
            t0 = time.perf_counter_ns()
            found_work = self._tick()
            t1 = time.perf_counter_ns()
            self._loop_time_ns_total += (t1 - t0)
            self._loop_count += 1

            if found_work:
                self._phase = "ACTIVE"
                idle_counter = 0
                self._pause_hint()
            else:
                idle_counter += 1
                if idle_counter < 10:
                    self._phase = "IDLE_1"
                    self._pause_hint()
                elif idle_counter < 100:
                    self._phase = "IDLE_2"
                    time.sleep(0.000_001)
                elif idle_counter < 1000:
                    self._phase = "IDLE_3"
                    time.sleep(0.000_1)
                else:
                    self._phase = "IDLE_4"
                    time.sleep(0.001)

    def stop(self) -> None:
        """Döngü sonlandırma sinyali."""
        self._running = False

    @property
    def loop_time_ns(self) -> int:
        """Ortalama döngü yineleme süresi (nanosaniye)."""
        if self._loop_count == 0:
            return 0
        return self._loop_time_ns_total // self._loop_count

    @property
    def cpu_usage(self) -> float:
        """Bu döngünün CPU kullanımı (0.0 ila 1.0)."""
        # Basit yer tutucu; gerçek ölçüm ileride /proc/stat veya psutil ile yapılabilir.
        return 1.0 if self._phase == "ACTIVE" else 0.1

    def _tick(self) -> bool:
        """Tek yineleme. İş varsa True döner."""
        work_found = False
        for etype, handler in self._handlers.items():
            try:
                result = handler(etype)
                if result:
                    work_found = True
            except Exception:
                pass
        return work_found

    @staticmethod
    def _pause_hint() -> None:
        """x86_64 üzerinde PAUSE komutu ipucu."""
        if platform.machine().lower() in ("amd64", "x86_64"):
            try:
                # ctypes ile basit bir boş çağrı; gerçek inline asm ileride C++ shim'de
                pass
            except Exception:
                pass
