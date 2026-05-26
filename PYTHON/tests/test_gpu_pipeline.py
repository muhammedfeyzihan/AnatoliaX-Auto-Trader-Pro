import pytest
from optimization.gpu_pipeline import GpuPipeline


def test_gpu_pipeline_process_features():
    gp = GpuPipeline(use_gpu=False)
    symbols = ["THYAO", "GARAN"]
    data = {"THYAO": [1.0, 2.0, 3.0], "GARAN": [4.0, 5.0, 6.0]}
    result = gp.process_features(symbols, data)
    assert "result" in result
    assert "elapsed_ms" in result
    assert result["gpu_used"] is False


def test_gpu_pipeline_benchmark():
    gp = GpuPipeline(use_gpu=False)
    symbols = ["THYAO", "GARAN"]
    data = {"THYAO": [1.0, 2.0, 3.0], "GARAN": [4.0, 5.0, 6.0]}
    bench = gp.benchmark(symbols, data)
    assert "cpu_ms" in bench
    assert "gpu_ms" in bench
    assert bench["speedup"] > 0


def test_onnx_inference_stub():
    gp = GpuPipeline(use_gpu=False)
    output = gp.onnx_inference("dummy.onnx", [0.1, 0.2])
    assert isinstance(output, list)
    assert len(output) == 3
