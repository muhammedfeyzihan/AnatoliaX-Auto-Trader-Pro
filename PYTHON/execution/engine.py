"""
engine.py — Birleşik Execution Engine (Backtest + Live)
Tek bir arayüz hem backtest hem canlı emir için.
"""
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class OrderStatus(Enum):
    PENDING = "pending"
    OPEN = "open"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    ERROR = "error"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    size: float = 0.0
    price: float = 0.0
    order_type: Literal["market", "limit"] = "market"
    status: OrderStatus = OrderStatus.PENDING
    filled_size: float = 0.0
    avg_fill_price: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    retries: int = 0
    max_retries: int = 3
    reject_reason: str = ""
    latency_ms: float = 0.0
    source: Literal["backtest", "live"] = "live"


class UnifiedExecutionEngine:
    """
    Tek execution motoru: backtest ve live modu aynı API ile.
    Live: gercek broker'a emir gonderir, retry/failover yapar.
    Backtest: anlik fiyat ile doldurur, kayit tutar.
    """

    def __init__(
        self,
        mode: Literal["backtest", "live"] = "live",
        broker_adapter: Optional[Callable] = None,
        slippage_model=None,
        commission_model=None,
        max_latency_ms: float = 500.0,
    ):
        self.mode = mode
        self.broker = broker_adapter
        self.slippage = slippage_model
        self.commission = commission_model
        self.max_latency_ms = max_latency_ms
        self.orders: Dict[str, Order] = {}
        self.history: List[Order] = []
        self._callbacks: List[Callable] = []

    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        size: float,
        price: float = 0.0,
        order_type: Literal["market", "limit"] = "market",
        sl: Optional[float] = None,
        tp: Optional[float] = None,
    ) -> Order:
        # K143: Emir validasyonu zorunlu
        from execution.order_validator import OrderValidator

        validator = OrderValidator()
        validation = validator.validate({
            "symbol": symbol,
            "side": side.value.upper(),
            "size": size,
            "price": price if price > 0 else 1.0,
            "sl": sl,
            "tp": tp,
        })
        if not validation["valid"]:
            order = Order(
                symbol=symbol.upper(),
                side=side,
                size=size,
                price=price,
                order_type=order_type,
                source=self.mode,
                status=OrderStatus.REJECTED,
            )
            order.reject_reason = "; ".join(validation["errors"])
            self.orders[order.id] = order
            self.history.append(order)
            self._notify(order)
            return order

        order = Order(
            symbol=symbol.upper(),
            side=side,
            size=size,
            price=price,
            order_type=order_type,
            source=self.mode,
        )
        self.orders[order.id] = order

        start = time.time()
        if self.mode == "backtest":
            self._execute_backtest(order)
        else:
            self._execute_live(order)
        order.latency_ms = (time.time() - start) * 1000

        order.updated_at = datetime.now(timezone.utc)
        self.history.append(order)
        self._notify(order)
        return order

    def _execute_backtest(self, order: Order):
        """Backtest: anlik fiyata slippage uygula, komisyon hesapla."""
        if self.slippage and order.price > 0:
            slip_rate = self.slippage.calculate(
                order.price * order.size, avg_daily_volume=500000, price=order.price
            )
            filled = (
                order.price * (1 + slip_rate)
                if order.side == OrderSide.BUY
                else order.price * (1 - slip_rate)
            )
        else:
            filled = order.price

        order.avg_fill_price = filled
        order.filled_size = order.size
        order.status = OrderStatus.FILLED

    def _execute_live(self, order: Order):
        """Live: broker adaptore gonder, retry mantigi."""
        if self.broker is None:
            order.status = OrderStatus.ERROR
            order.reject_reason = "Broker adapter not configured"
            return

        try:
            result = self.broker(order)
            if result.get("filled"):
                order.status = OrderStatus.FILLED
                order.filled_size = result.get("filled_size", order.size)
                order.avg_fill_price = result.get("avg_price", order.price)
            elif result.get("partial"):
                order.status = OrderStatus.PARTIAL
                order.filled_size = result.get("filled_size", 0.0)
                order.avg_fill_price = result.get("avg_price", order.price)
            else:
                order.status = OrderStatus.REJECTED
                order.reject_reason = result.get("reason", "unknown")
        except Exception as e:
            order.status = OrderStatus.ERROR
            order.reject_reason = str(e)
            if order.retries < order.max_retries:
                order.retries += 1
                self._execute_live(order)

    def cancel_order(self, order_id: str) -> bool:
        order = self.orders.get(order_id)
        if not order or order.status in (OrderStatus.FILLED, OrderStatus.CANCELLED):
            return False
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now(timezone.utc)
        self._notify(order)
        return True

    def get_open_orders(self) -> List[Order]:
        return [
            o for o in self.orders.values()
            if o.status in (OrderStatus.PENDING, OrderStatus.OPEN, OrderStatus.PARTIAL)
        ]

    def reconcile(self, external_orders: List[dict]):
        """Disaridan gelen emir listesiyle ic durumu eslestir."""
        for ext in external_orders:
            oid = ext.get("id")
            if oid in self.orders:
                order = self.orders[oid]
                order.status = OrderStatus(ext.get("status", "pending"))
                order.filled_size = ext.get("filled_size", order.filled_size)
                order.avg_fill_price = ext.get("avg_price", order.avg_fill_price)
                order.updated_at = datetime.now(timezone.utc)

    def on_fill(self, callback: Callable):
        self._callbacks.append(callback)

    def _notify(self, order: Order):
        for cb in self._callbacks:
            cb(order)


class SmartOrderSlicer:
    """
    Execution Microstructure Engine — Module 1 (Phase 1)
    Smart order slicing: TWAP, VWAP, POV with toxicity-aware routing.
    """

    def __init__(self, total_volume: float, slices: int = 10):
        self.total_volume = total_volume
        self.slices = slices
        self.slice_volume = total_volume / slices

    def twap(self) -> list[float]:
        """TWAP: v_i = V / n (equal slices)."""
        return [self.slice_volume] * self.slices

    def vwap(self, volume_weights: list[float]) -> list[float]:
        """VWAP: v_i = V * (w_i / sum(w))."""
        total_w = sum(volume_weights) or 1.0
        return [self.total_volume * (w / total_w) for w in volume_weights]

    def pov(self, market_volumes: list[float], participation_rate: float = 0.1) -> list[float]:
        """POV: v_i = alpha * market_vol_i."""
        return [participation_rate * mv for mv in market_volumes]


class MicrostructureAnalyzer:
    """
    Execution Microstructure Engine — Module 1 (Phase 1)
    Queue position modeling, hidden liquidity detection, adverse selection.
    """

    def __init__(self):
        self.imbalance_history: list[float] = []

    def queue_position(
        self,
        order_size: float,
        book_depth: float,
        arrival_rate: float,
    ) -> float:
        """Q(t) = f(order_size, book_depth, arrival_rate)."""
        if book_depth <= 0 or arrival_rate <= 0:
            return 0.0
        return order_size / (book_depth * arrival_rate)

    def hidden_liquidity_imbalance(
        self,
        bid_vol: float,
        ask_vol: float,
    ) -> float:
        """I = (bid_vol - ask_vol) / (bid_vol + ask_vol)."""
        denom = bid_vol + ask_vol
        if denom == 0:
            return 0.0
        return (bid_vol - ask_vol) / denom

    def adverse_selection_spread(
        self,
        execution_price: float,
        midprice_future: float,
    ) -> float:
        """Realized Spread = 2 * (execution_price - midprice_t+5min)."""
        return 2.0 * (execution_price - midprice_future)

    def vpin(self, buy_vol: float, sell_vol: float, window_vol: float) -> float:
        """Volume-synchronized Probability of Informed Trading."""
        if window_vol <= 0:
            return 0.0
        return abs(buy_vol - sell_vol) / window_vol


class ToxicityRouter:
    """
    Toxicity-aware execution routing via VPIN.
    """

    def __init__(self, vpin_threshold: float = 0.7):
        self.vpin_threshold = vpin_threshold

    def route(self, vpin: float) -> str:
        """If toxic_flow_probability > 0.7, switch to passive execution."""
        if vpin > self.vpin_threshold:
            return "passive"
        return "aggressive"
