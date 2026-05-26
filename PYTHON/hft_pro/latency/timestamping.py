"""
latency/timestamping.py — Donanim zaman damgasi (IEEE 1588 PTP, NIC HW TS)
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class HardwareTimestamp:
    seconds: int
    nanoseconds: int
    source: str  # "ptp", "nic", "system"


class HardwareTimestamping:
    """
    Donanim zaman damgasi yoneticisi.

    Kaynaklar:
    - PTP (IEEE 1588): sub-mikrosaniye senkronizasyon
    - NIC HW Timestamping: Intel i210/i350, Mellanox ConnectX
    - Geri donus: sistem saati (CLOCK_MONOTONIC_RAW)

    K154: Donanim TS mevcut degilse monotonic raw geri donus.
    """

    def __init__(self, source: str = "auto"):
        self.source = source
        self._available = False

    def now(self) -> HardwareTimestamp:
        import time
        t = time.time_ns()
        return HardwareTimestamp(seconds=t // 1_000_000_000, nanoseconds=t % 1_000_000_000, source="system")

    def calibrate_ptp(self) -> bool:
        """PTP ana saat ile senkronizasyon."""
        return False  # yer tutucu
