"""
Test: PYTHON.risk.pre_trade_engine
Pre-trade risk gate: KillSwitch, Exposure, Heat, Rate Limit.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.message_bus import MessageBus
from common.events import EventType, OrderEvent
from risk.pre_trade_engine import PreTradeRiskEngine
from risk.kill_switch import KillSwitch


class TestPreTradeRiskEngine:
    def _make_bus_and_engine(self, **kwargs):
        bus = MessageBus()
        engine = PreTradeRiskEngine(bus, **kwargs)
        engine.set_capital(1_000_000)
        engine.set_positions([])
        engine.start()
        return bus, engine

    def test_killswitch_blocks(self):
        bus, engine = self._make_bus_and_engine()
        engine.kill_switch._trigger("test")
        received = []
        bus.subscribe(EventType.ORDER_REJECTED, lambda e: received.append(e))
        bus.publish(OrderEvent(order_id="o1", symbol="THYAO", side="BUY", size=100, price=103.0))
        assert len(received) == 1
        assert "KillSwitch" in received[0].metadata["reason"]

    def test_rate_limit_blocks(self):
        bus, engine = self._make_bus_and_engine(max_orders_per_minute=2)
        received = []
        bus.subscribe(EventType.ORDER_REJECTED, lambda e: received.append(e))
        for i in range(5):
            bus.publish(OrderEvent(order_id=f"o{i}", symbol="THYAO", side="BUY", size=1, price=100.0))
        # 2'si rate limit içinde, 3.'ü RED olmalı
        assert len(received) >= 1
        assert any("Rate limit" in r.metadata.get("reason", "") for r in received)

    def test_exposure_limit_blocks(self):
        bus, engine = self._make_bus_and_engine()
        # Çok büyük pozisyon
        engine.set_positions([{"symbol": "THYAO", "size": 100000, "price": 100.0}])
        received = []
        bus.subscribe(EventType.ORDER_REJECTED, lambda e: received.append(e))
        bus.publish(OrderEvent(order_id="o1", symbol="THYAO", side="BUY", size=100, price=100.0))
        assert len(received) == 1

    def test_heat_limit_blocks(self):
        bus, engine = self._make_bus_and_engine()
        # SL çok uzakta = yüksek heat
        engine.set_positions([{"symbol": "THYAO", "size": 50000, "entry_price": 100.0, "stop_loss": 1.0}])
        received = []
        bus.subscribe(EventType.ORDER_REJECTED, lambda e: received.append(e))
        bus.publish(OrderEvent(order_id="o1", symbol="THYAO", side="BUY", size=100, price=100.0))
        assert len(received) == 1
        assert any("heat" in r.metadata.get("reason", "").lower() for r in received)

    def test_approved(self):
        bus, engine = self._make_bus_and_engine()
        approved = []
        bus.subscribe(EventType.ORDER_ACCEPTED, lambda e: approved.append(e))
        bus.publish(OrderEvent(order_id="o1", symbol="THYAO", side="BUY", size=100, price=103.0))
        assert len(approved) == 1
        assert approved[0].metadata["symbol"] == "THYAO"

    def test_risk_event_emitted(self):
        bus, engine = self._make_bus_and_engine()
        risks = []
        bus.subscribe(EventType.RISK_APPROVED, lambda e: risks.append(e))
        bus.publish(OrderEvent(order_id="o1", symbol="THYAO", side="BUY", size=100, price=103.0))
        assert len(risks) == 1
        assert risks[0].passed is True

    def test_stop_unsubscribes(self):
        bus, engine = self._make_bus_and_engine()
        engine.stop()
        received = []
        bus.subscribe(EventType.ORDER_REJECTED, lambda e: received.append(e))
        engine.kill_switch._trigger("test")
        bus.publish(OrderEvent(order_id="o1", symbol="THYAO", side="BUY", size=100, price=103.0))
        # stop sonrasi handler calismamali ama bus'ta manuel subscriber ekledik
        # Bu test bus'un unsubscribe calistigini dogrular
        assert len(received) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
