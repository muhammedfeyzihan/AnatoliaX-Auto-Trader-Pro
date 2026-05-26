"""
gpu/cuda_kernels.py — CuPy RawKernel derlemeleri
"""
from typing import Optional


class CUDAKernels:
    """
    Derlenmiş CuPy RawKernel koleksiyonu.

    Kernels:
    - ema_update: üstel hareketli ortalama (tick bazlı)
    - book_update: emir defteri seviye güncelleme (GPU paralel)
    - correlation: çoklu sembol korelasyon matrisi

    Kullanım: kernel = CUDAKernels().ema_update; kernel((blocks,), (threads,), (arg1, arg2))
    """

    _EMA_SRC = r"""
    extern "C" __global__ void ema_update(const float* price, float* ema, int n, float alpha) {
        int idx = blockDim.x * blockIdx.x + threadIdx.x;
        if (idx < n) {
            if (idx == 0) ema[idx] = price[idx];
            else ema[idx] = alpha * price[idx] + (1.0f - alpha) * ema[idx - 1];
        }
    }
    """

    _BOOK_SRC = r"""
    extern "C" __global__ void book_update(float* levels, const float* deltas, int n) {
        int idx = blockDim.x * blockIdx.x + threadIdx.x;
        if (idx < n) {
            levels[idx] += deltas[idx];
            if (levels[idx] < 0.0f) levels[idx] = 0.0f;
        }
    }
    """

    _CORR_SRC = r"""
    extern "C" __global__ void correlation(const float* data, float* out, int rows, int cols) {
        int i = blockIdx.y * blockDim.y + threadIdx.y;
        int j = blockIdx.x * blockDim.x + threadIdx.x;
        if (i < rows && j < rows) {
            float sum_x = 0, sum_y = 0, sum_xy = 0, sum_x2 = 0, sum_y2 = 0;
            for (int k = 0; k < cols; k++) {
                float x = data[i * cols + k];
                float y = data[j * cols + k];
                sum_x += x; sum_y += y; sum_xy += x * y; sum_x2 += x * x; sum_y2 += y * y;
            }
            float n = (float)cols;
            float num = n * sum_xy - sum_x * sum_y;
            float den = sqrtf((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y));
            out[i * rows + j] = den > 0 ? num / den : 0;
        }
    }
    """

    def __init__(self):
        self._ema: Optional[object] = None
        self._book: Optional[object] = None
        self._corr: Optional[object] = None
        self._compiled = False

    def _compile(self) -> None:
        try:
            import cupy as cp
            self._ema = cp.RawKernel(self._EMA_SRC, "ema_update")
            self._book = cp.RawKernel(self._BOOK_SRC, "book_update")
            self._corr = cp.RawKernel(self._CORR_SRC, "correlation")
            self._compiled = True
        except Exception:
            self._compiled = False

    @property
    def ema_update(self) -> Optional[object]:
        if not self._compiled:
            self._compile()
        return self._ema

    @property
    def book_update(self) -> Optional[object]:
        if not self._compiled:
            self._compile()
        return self._book

    @property
    def correlation(self) -> Optional[object]:
        if not self._compiled:
            self._compile()
        return self._corr

    def is_available(self) -> bool:
        self._compile()
        return self._compiled
