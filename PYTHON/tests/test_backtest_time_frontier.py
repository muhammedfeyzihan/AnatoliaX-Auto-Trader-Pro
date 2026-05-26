import pytest
from backtest.time_frontier import TimeFrontier, Tick


def test_time_frontier_zero_lookahead():
    tf = TimeFrontier()
    tf.ingest_tick(Tick(timestamp=1.0, price=100.0, volume=1000))
    tf.ingest_tick(Tick(timestamp=2.0, price=101.0, volume=500))
    assert tf.step().timestamp == 1.0
    assert tf.step().timestamp == 2.0
    assert tf.step() is None


def test_available_data_constraint():
    tf = TimeFrontier()
    tf.ingest_tick(Tick(timestamp=5.0, price=100.0, volume=1000))
    data = tf.available_data()
    assert len(data) == 1


def test_agent_latency():
    tf = TimeFrontier()
    lat = tf.agent_latency()
    assert lat >= 0
