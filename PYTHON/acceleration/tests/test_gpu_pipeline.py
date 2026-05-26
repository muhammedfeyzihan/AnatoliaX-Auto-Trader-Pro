"""
tests/test_gpu_pipeline.py — GPU pipeline testleri
"""
import unittest
from PYTHON.acceleration.gpu.gpu_pipeline import GPUPipeline


class TestGPUPipeline(unittest.TestCase):
    def test_init(self):
        gp = GPUPipeline()
        self.assertIsNotNone(gp)

    def test_cpu_fallback(self):
        gp = GPUPipeline()
        data = [1.0] * 2000
        result = gp.update(data)
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
