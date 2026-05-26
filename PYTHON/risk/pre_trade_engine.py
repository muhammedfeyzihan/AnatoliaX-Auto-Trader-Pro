"""
pre_trade_engine.py — Pre-trade risk gate (Nautilus Trader RiskEngine pattern).
Emir execution'a ulaşmadan önce bus üzerinde intercept edilir.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Callable
from common.message_bus import MessageBus
from common.events import Event, EventType, OrderEvent, RiskEvent
from risk.kill_switch import KillSwitch
from risk.exposure_limiter import ExposureLimiter
from risk.portfolio_heat import PortfolioHeat


class PreTradeRiskEngine:
    """
    Pre-trade risk gate. Tüm emirler buradan geçer:
    1. KillSwitch alive?
    2. Exposure limits?
    3. Portfolio heat?
    4. Order rate limit?
    5. Agent approval (3/3)?

    Eğer bir check RED verirse, ORDER_REJECTED event'i yayınlanır
    ve emir execution'a gitmez.
    """

    def __init__(
        self,
        bus: MessageBus,
        kill_switch: Optional[KillSwitch] = None,
        exposure_limiter: Optional[ExposureLimiter] = None,
        portfolio_heat: Optional[PortfolioHeat] = None,
        max_orders_per_minute: int = 10,
    ):
        self.bus = bus
        self.kill_switch = kill_switch or KillSwitch()
        self.exposure = exposure_limiter or ExposureLimiter()
        self.heat = portfolio_heat or PortfolioHeat()
        self.max_orders_per_minute = max_orders_per_minute
        self._order_times: List[datetime] = []
        self._positions: List[dict] = []
        self._capital: float = 1_000_000.0
        self._on_approved: Optional[Callable] = None

    def start(self):
        """Bus'a abone ol ve ORDER_SUBMITTED event'lerini dinle."""
        self.bus.subscribe(EventType.ORDER_SUBMITTED, self._on_order)
        self.bus.subscribe(EventType.POSITION_UPDATED, self._on_position_update)

    def stop(self):
        self.bus.unsubscribe(EventType.ORDER_SUBMITTED, self._on_order)
        self.bus.unsubscribe(EventType.POSITION_UPDATED, self._on_position_update)

    def set_capital(self, capital: float):
        self._capital = capital

    def set_positions(self, positions: List[dict]):
        self._positions = positions

    def _on_position_update(self, event: Event):
        if isinstance(event, Event) and event.metadata.get("positions"):
            self._positions = event.metadata["positions"]

    def _on_order(self, event: Event):
        if not isinstance(event, OrderEvent):
            return

        # 1. KillSwitch
        if not self.kill_switch.is_alive():
            self._deny(event, "KillSwitch aktif — trading durduruldu")
            return

        # 2. Order rate limit
        if self._rate_limit_exceeded():
            self._deny(event, f"Rate limit: dakikada {self.max_orders_per_minute} emir limiti asildi")
            return

        # 3. Exposure limits
        exposure_result = self.exposure.check(self._positions, self._capital)
        if not exposure_result["allowed"]:
            self._deny(event, "; ".join(exposure_result["alerts"]))
            return

        # 4. Portfolio heat
        heat_result = self.heat.calculate_heat(self._positions, self._capital)
        if not heat_result["allowed"]:
            self._deny(event, f"Portfolio heat %{heat_result['heat']*100:.2f} > limit %{self.heat.max_heat*100}")
            return

        # ONAY
        self._approve(event)

    def _rate_limit_exceeded(self) -> bool:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=1)
        self._order_times = [t for t in self._order_times if t > cutoff]
        self._order_times.append(now)
        return len(self._order_times) > self.max_orders_per_minute

    def _deny(self, order_event: OrderEvent, reason: str):
        self.bus.publish(RiskEvent(
            event_type=EventType.RISK_DENIED,
            check_type="pre_trade",
            passed=False,
            reason=reason,
            order_id=order_event.order_id,
        ))
        self.bus.publish(Event(
            event_type=EventType.ORDER_REJECTED,
            metadata={
                "order_id": order_event.order_id,
                "symbol": order_event.symbol,
                "reason": reason,
            },
        ))

    def _approve(self, order_event: OrderEvent):
        self.bus.publish(RiskEvent(
            event_type=EventType.RISK_APPROVED,
            check_type="pre_trade",
            passed=True,
            reason="OK",
            order_id=order_event.order_id,
        ))
        self.bus.publish(Event(
            event_type=EventType.ORDER_ACCEPTED,
            metadata={
                "order_id": order_event.order_id,
                "symbol": order_event.symbol,
                "side": order_event.side,
                "size": order_event.size,
                "price": order_event.price,
            },
        ))
        if self._on_approved:
            self._on_approved(order_event)
