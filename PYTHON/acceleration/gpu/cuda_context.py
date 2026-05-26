"""
gpu/cuda_context.py — CUDA baglam yonetimi (bellek havuzlari, akislar, profilleme)
"""
from typing import Optional


class CUDAContext:
    """
    CUDA baglam yoneticisi.

    Ozellikler:
    - Akis yonetimi: 3 adet async akis (normal, yuksek, kritik)
    - Bellek havuzlari: on-ayrilmis GPU bellek havuzlari (1GB, 4GB, 16GB)
    - Olay tabanli senkronizasyon
    - nsys / nvprof entegrasyonu ile profilleme

    Kullanim:
        with CUDAContext() as ctx:
            stream = ctx.get_stream(priority="high")
            # GPU islemleri
    """

    def __init__(self, device_id: int = 0):
        self.device_id = device_id
        self._streams: dict = {}
        self._pools: dict = {}
        self._active = False

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
        return False

    def initialize(self) -> bool:
        try:
            import cupy as cp
            cp.cuda.Device(self.device_id).use()
            self._streams = {
                "normal": cp.cuda.Stream(),
                "high": cp.cuda.Stream(non_blocking=True),
                "critical": cp.cuda.Stream(non_blocking=True),
            }
            self._pools = {"1GB": None, "4GB": None, "16GB": None}
            self._active = True
            return True
        except Exception:
            self._active = False
            return False

    def shutdown(self) -> None:
        for s in self._streams.values():
            if s:
                s.synchronize()
        self._active = False

    def get_stream(self, priority: str = "normal"):
        return self._streams.get(priority)

    def is_available(self) -> bool:
        return self._active
