"""
gpu/numba_kernels.py — CPU fallback numba JIT hizlandirici
"""
from typing import Optional


class NumbaKernels:
    """
    Numba JIT hizlandirici (CUDA yoksa CPU fallback).

    Kernel'ler:
    - EMA: jit(nopython=True) ile vektorel EMA
    - RSI: jit ile RSI hesabi
    - MACD: jit ile MACD hizli
    - Z-Score: jit ile anomali tespiti

    K181: Numba yuklenemezse saf NumPy calisir; performans duser ama dogruluk korunur.
    """

    def __init__(self):
        self._has_numba = self._try_import()

    def _try_import(self) -> bool:
        try:
            import numba  # noqa
            return True
        except Exception:
            return False

    def ema(self, arr, span: int):
        if self._has_numba:
            return self._ema_numba(arr, span)
        return self._ema_numpy(arr, span)

    def _ema_numpy(self, arr, span: int):
        import numpy as np
        alpha = 2.0 / (span + 1)
        out = np.empty_like(arr, dtype=np.float64)
        out[0] = arr[0]
        for i in range(1, len(arr)):
            out[i] = alpha * arr[i] + (1 - alpha) * out[i - 1]
        return out

    def _ema_numba(self, arr, span: int):
        import numba
        import numpy as np

        @numba.jit(nopython=True)
        def _ema(a, s):
            alpha = 2.0 / (s + 1)
            out = np.empty_like(a, dtype=np.float64)
            out[0] = a[0]
            for i in range(1, len(a)):
                out[i] = alpha * a[i] + (1 - alpha) * out[i - 1]
            return out

        return _ema(np.asarray(arr, dtype=np.float64), span)
