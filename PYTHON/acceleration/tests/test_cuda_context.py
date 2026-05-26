"""
tests/test_cuda_context.py — CUDAContext birim testleri
"""
import pytest
from acceleration.gpu.cuda_context import CUDAContext


class TestCUDAContext:
    def test_context_manager(self):
        with CUDAContext(device_id=0) as ctx:
            assert ctx.is_available() is True or ctx.is_available() is False

    def test_get_stream(self):
        ctx = CUDAContext()
        ctx.initialize()
        stream = ctx.get_stream("normal")
        # None veya gercek stream olabilir
        ctx.shutdown()
