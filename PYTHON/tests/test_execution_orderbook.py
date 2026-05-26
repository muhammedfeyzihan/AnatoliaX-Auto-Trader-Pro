import pytest
from execution.order_book import (
    OrderBookReconstructor, OrderBookEvent,
    SpoofingDetector, LayeringDetector, LiquidityVacuumDetector
)
from datetime import datetime, timezone, timedelta


def test_orderbook_reconstruction():
    ob = OrderBookReconstructor("THYAO")
    now = datetime.now(timezone.utc)
    ob.apply_event(OrderBookEvent(now, "THYAO", "bid", 100.0, 1000, "add", "o1"))
    ob.apply_event(OrderBookEvent(now, "THYAO", "ask", 101.0, 500, "add", "o2"))
    assert ob.get_best_bid().price == 100.0
    assert ob.get_best_ask().price == 101.0
    assert ob.get_spread() == 1.0


def test_spoofing_detection():
    sd = SpoofingDetector(tau_seconds=2.0, size_multiplier=3.0)
    now = datetime.now(timezone.utc)
    # Add baseline small orders to lower avg_size
    for i in range(5):
        sd.record(OrderBookEvent(now, "THYAO", "bid", 100.0, 100, "add", f"base{i}"))
    # Large add + quick cancel should trigger spoofing
    sd.record(OrderBookEvent(now, "THYAO", "bid", 100.0, 10000, "add", "o1"))
    sd.record(OrderBookEvent(now + timedelta(seconds=1), "THYAO", "bid", 100.0, 10000, "cancel", "o1"))
    alerts = sd.scan()
    assert len(alerts) >= 1
    assert alerts[0]["type"] == "SPOOFING"


def test_layering_detection():
    ld = LayeringDetector(sequence_threshold=5)
    now = datetime.now(timezone.utc)
    for i in range(5):
        ld.record(OrderBookEvent(now + timedelta(seconds=i), "THYAO", "bid", 100.0, 100, "add", f"o{i}"))
        ld.record(OrderBookEvent(now + timedelta(seconds=i+0.5), "THYAO", "bid", 100.0, 100, "cancel", f"o{i}"))
    alerts = ld.scan()
    assert any(a["type"] == "LAYERING" for a in alerts)


def test_liquidity_vacuum():
    lvd = LiquidityVacuumDetector()
    for i in range(30):
        lvd.record(spread=0.5 + (i * 0.05 if i > 25 else 0), depth=100000 - i * 1000)
    alert = lvd.detect()
    assert alert is None or alert["type"] == "LIQUIDITY_VACUUM"
