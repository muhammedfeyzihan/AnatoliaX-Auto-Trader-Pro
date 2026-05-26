import pytest
from infrastructure.hardware_optimizer import HardwareOptimizer, LockFreeQueue


def test_system_info():
    opt = HardwareOptimizer()
    info = opt.get_system_info()
    assert "cpu_count" in info
    assert info["cpu_count"] > 0


def test_benchmark_hot_path():
    opt = HardwareOptimizer()
    result = opt.benchmark_hot_path(lambda: None, iterations=1000)
    assert result["iterations"] == 1000
    assert result["avg_ns"] >= 0


def test_lock_free_queue():
    q = LockFreeQueue(maxlen=100)
    q.enqueue(1)
    q.enqueue(2)
    assert q.dequeue() == 1
    assert q.dequeue() == 2
    assert q.is_empty() is True
