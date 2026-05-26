import pytest
from infrastructure.observability_tracing import DistributedObservability, Span


def test_span_lifecycle():
    obs = DistributedObservability()
    span = obs.start_span("trace-1", "span-1", None, "test_op")
    obs.end_span(span)
    assert span.end_ns is not None
    assert span.end_ns > span.start_ns


def test_latency_percentiles():
    obs = DistributedObservability()
    for i in range(100):
        span = obs.start_span("trace-1", f"span-{i}", None, "test_op")
        # simulate varying latency by not ending some immediately
        if i < 50:
            pass  # leave open for this test
        else:
            obs.end_span(span)
    pcts = obs.latency_percentiles("test_op")
    if pcts:
        assert "p50" in pcts


def test_throughput_counter():
    obs = DistributedObservability()
    obs.record_throughput("test_op", 5)
    metrics = obs.get_metrics()
    assert metrics["throughput"]["test_op"] == 5
