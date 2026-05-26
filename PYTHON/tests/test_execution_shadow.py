import pytest
from execution.shadow_execution import ShadowExecutionEnvironment


def test_create_shadow():
    env = ShadowExecutionEnvironment()
    s = env.create_shadow("o1", "THYAO", "buy", 1000, 105.0)
    assert s.live_order_id == "o1"


def test_divergence_alert():
    env = ShadowExecutionEnvironment(divergence_threshold=0.1)
    env.create_shadow("o1", "THYAO", "buy", 1000, 105.0)
    env.record_live_fill("o1", 105.2, 50.0)
    alert = env.record_shadow_fill("o1", 105.5, 80.0, 0.5)
    assert alert["divergence_alert"] is True
    assert alert["latency_alert"] is True


def test_divergence_stats():
    env = ShadowExecutionEnvironment()
    env.create_shadow("o1", "THYAO", "buy", 1000, 105.0)
    env.record_live_fill("o1", 105.2, 50.0)
    env.record_shadow_fill("o1", 105.3, 80.0, 0.5)
    stats = env.get_divergence_stats()
    assert "mean_divergence" in stats
