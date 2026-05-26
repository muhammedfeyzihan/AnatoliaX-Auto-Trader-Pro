"""
tests/test_onnx_runtime.py — ONNXGPUInference birim testleri
"""
import pytest
from acceleration.gpu.onnx_runtime import ONNXGPUInference


class TestONNXGPUInference:
    def test_load_missing_model(self):
        inf = ONNXGPUInference("nonexistent.onnx")
        assert inf.load() is False

    def test_predict_without_load(self):
        inf = ONNXGPUInference("dummy.onnx")
        assert inf.predict({"x": [1.0]}) is None
