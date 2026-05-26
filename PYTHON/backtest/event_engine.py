"""
event_engine.py — Event-driven backtest engine.
Replays tick/bar data through the MessageBus using the same
UnifiedExecutionEngine path as live mode, achieving backtest/live parity.
Inspired by Nautilus Trader's deterministic event loop.
"""
import pandas as pd
import numpy as np
from typing import Callable, Optional, Dict, List
from datetime import datetime, timezone

from common.message_bus import MessageBus
from common.events import Event, EventType, OrderEvent, FillEvent, PositionEvent
from execution.engine import UnifiedExecutionEngine, OrderSide, OrderStatus
from backtest.fill_model import FillModel, ImmediateFillModel
from backtest.commission import CommissionModel


class EventDrivenBacktestEngine:
    """
    Event-driven backtest: market data → bus → signal → risk → execution → fill.
    Uses the same UnifiedExecutionEngine as live mode for parity.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        bus: Optional[MessageBus] = None,
        fill_model: Optional[FillModel] = None,
        commission_model: Optional[CommissionModel] = None,
        initial_capital: float = 100_000.0,
        position_size_pct: float = 0.02,
        signal_threshold: int = 1,  # Signal >= 1 to enter
        sl_pct: float = 0.015,
        tp_pct: float = 0.03,
        pre_trade_engine: Optional["PreTradeRiskEngine"] = None,
    ):
        self.df = df.copy()
        self.bus = bus or MessageBus()
        self.fill_model = fill_model or ImmediateFillModel()
        self.commission = commission_model or CommissionModel()
        self.initial_capital = initial_capital
        self.position_size_pct = position_size_pct
        self.signal_threshold = signal_threshold
        self.sl_pct = sl_pct
        self.tp_pct = tp_pct

        self.current_capital = initial_capital
        self.trades: List[dict] = []
        self.equity_curve: List[tuple] = []
        self.open_positions: List[dict] = []
        self._signal_func: Optional[Callable] = None

        # Internal execution engine (live mode) for parity
        self._exec = UnifiedExecutionEngine(mode="live")
        self._exec.on_fill(self._on_fill)

        # Pre-trade risk engine (optional) — intercepts orders before execution
        self._pre_trade = pre_trade_engine
        if self._pre_trade is not None:
            self._pre_trade.bus = self.bus  # Ensure shared bus

        # Subscribe to our own events
        self.bus.subscribe(EventType.SIGNAL_GENERATED, self._on_signal)
        self.bus.subscribe(EventType.ORDER_ACCEPTED, self._on_order_accepted)

    def set_signal_function(self, fn: Callable):
        """Set a signal function that receives a bar row and returns a score/dict."""
        self._signal_func = fn

    def run(self) -> dict:
        """Replay each bar as a market data event through the bus."""
        for i, (ts, row) in enumerate(self.df.iterrows()):
            self._process_bar(i, ts, row)

        # Close remaining positions at last price
        if not self.df.empty:
            last_row = self.df.iloc[-1]
            for pos in self.open_positions[:]:
                self._close_position(pos, last_row["close"], "CLOSE")

        return {
            "trades": pd.DataFrame(self.trades),
            "equity": pd.DataFrame(self.equity_curve, columns=["timestamp", "equity"]).set_index("timestamp"),
            "final_capital": self.current_capital,
            "total_return": (self.current_capital - self.initial_capital) / self.initial_capital,
        }

    def _process_bar(self, idx: int, timestamp, row: pd.Series):
        # Publish market data event
        self.bus.publish(Event(
            event_type=EventType.MARKET_DATA,
            metadata={
                "timestamp": timestamp,
                "symbol": row.get("symbol", "UNKNOWN"),
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "volume": row.get("volume", 0),
                "signal": row.get("Signal", 0),
                "signal_score": row.get("Signal_Score", 0),
            },
        ))

        # Evaluate signal
        signal = row.get("Signal", 0)
        if signal >= self.signal_threshold and len(self.open_positions) < 5:
            price = row["close"]
            size = (self.current_capital * self.position_size_pct) / price
            self.bus.publish(OrderEvent(
                order_id=f"sim_{idx}",
                symbol=row.get("symbol", "THYAO"),
                side="BUY",
                size=size,
                price=price,
                order_type="market",
            ))

        # Check open positions for SL/TP
        self._check_exits(idx, row)

        self.equity_curve.append((timestamp, self.current_capital))

    def _on_signal(self, event: Event):
        """Signal handler placeholder (can be overridden)."""
        pass

    def _on_order_accepted(self, event: Event):
        """When order is accepted by pre-trade risk, execute via fill model."""
        meta = event.metadata
        price = meta.get("price", 0)
        size = meta.get("size", 0)
        side = meta.get("side", "BUY")
        symbol = meta.get("symbol", "")
        order_id = meta.get("order_id", "")

        if price <= 0 or size <= 0:
            return

        # Fill model decides if and at what price
        if not self.fill_model.can_fill(price, side, size):
            return

        fill_price = self.fill_model.fill_price(price, side, size)
        comm = self.commission.calculate(fill_price, size)

        self.bus.publish(FillEvent(
            order_id=order_id,
            filled_size=size,
            avg_fill_price=fill_price,
            commission=comm["total"],
            remaining=0.0,
        ))

    def _on_fill(self, order):
        """Callback from UnifiedExecutionEngine.on_fill."""
        if order.status == OrderStatus.FILLED:
            pos = {
                "order_id": order.id,
                "symbol": order.symbol,
                "entry_price": order.avg_fill_price,
                "size": order.filled_size,
                "commission": 0.0,  # Will be set on exit
            }
            self.open_positions.append(pos)

    def _check_exits(self, idx, row):
        price = row["close"]
        for pos in self.open_positions[:]:
            entry = pos["entry_price"]
            sl = entry * (1 - self.sl_pct)
            tp = entry * (1 + self.tp_pct)
            if price <= sl:
                self._close_position(pos, price, "SL")
            elif price >= tp:
                self._close_position(pos, price, "TP")

    def _close_position(self, pos: dict, exit_price: float, reason: str):
        size = pos["size"]
        entry = pos["entry_price"]
        comm = self.commission.calculate(exit_price, size)
        gross = (exit_price - entry) * size
        net = gross - comm["total"]
        self.current_capital += net

        self.trades.append({
            "entry_price": entry,
            "exit_price": exit_price,
            "size": size,
            "reason": reason,
            "gross_pnl": gross,
            "net_pnl": net,
            "commission": comm["total"],
        })
        self.open_positions.remove(pos)

    def get_bus(self) -> MessageBus:
        return self.bus
