"""
tests/test_cuda_kernels.py — CUDA kernel testleri
"""
import unittest
from PYTHON.acceleration.gpu.cuda_kernels import CUDAKernels


class TestCUDAKernels(unittest.TestCase):
    def test_ema_kernel_exists(self):
        ck = CUDAKernels()
        self.assertTrue(hasattr(ck, 'ema_kernel') or hasattr(ck, '_cpu_ema'))

    def test_book_update_exists(self):
        ck = CUDAKernels()
        self.assertTrue(hasattr(ck, 'book_update_kernel') or hasattr(ck, '_cpu_book_update'))


if __name__ == "__main__":
    unittest.main()
