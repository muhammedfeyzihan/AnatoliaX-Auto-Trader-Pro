"""
hft_backtest.py — Tick-level HFT backtest engine.
Replays ticks through TickAggregator -> Signal -> Risk -> Position -> Order lifecycle.
Inspired by hftbacktest's event-driven tick replay.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from hft.tick_aggregator import TickAggregator
from hft.signal_generator import generate_signal_from_df
from hft.risk_filter import RiskFilter, RiskFilterResult
from hft.position_manager import HFTPositionManager
from hft.order_manager import HFTOrderManager, HFTOrderStatus
from hft.latency_tracker import LatencyTracker
from risk.account import Account
from backtest.commission import CommissionModel
from backtest.fill_model import FillModel, ImmediateFillModel


class HFTBacktestEngine:
    """
    Tick-level HFT backtest.
    Processes each tick as a market data event.
    """

    def __init__(
        self,
        tick_df: pd.DataFrame,
        strategy: str = "m1_momentum",
        interval_seconds: int = 60,
        initial_capital: float = 100_000.0,
        fill_model: Optional[FillModel] = None,
        commission_rate: float = 0.001,
        bsmv_rate: float = 0.001,
        risk_filter: Optional[RiskFilter] = None,
    ):
        self.tick_df = tick_df.copy()
        self.strategy = strategy
        self.interval = interval_seconds

        self.account = Account(initial_cash=initial_capital, max_position_value_pct=1.0)
        self.pos_manager = HFTPositionManager(self.account)
        self.order_manager = HFTOrderManager()
        self.aggregator = TickAggregator(interval_seconds=interval_seconds)
        self.latency = LatencyTracker()
        self.fill_model = fill_model or ImmediateFillModel()
        self.commission = CommissionModel(commission_rate=commission_rate, bsmv_rate=bsmv_rate)
        self.risk = risk_filter or RiskFilter()

        self.trades: list = []
        self.equity_curve: list = []
        self._bar_counter = 0

    def run(self) -> dict:
        """Replay ticks and run strategy."""
        for _, row in self.tick_df.iterrows():
            self._process_tick(row)

        # Close remaining positions at last price
        if not self.tick_df.empty:
            last_price = self.tick_df["price"].iloc[-1]
            symbols = list(self.account.positions.keys())
            for sym in symbols:
                pos = self.account.get_position(sym)
                if pos and pos.is_open:
                    self._exit(sym, pos.quantity, last_price, "CLOSE")

        return {
            "trades": pd.DataFrame(self.trades),
            "equity": pd.DataFrame(self.equity_curve, columns=["timestamp", "equity"]).set_index("timestamp") if self.equity_curve else pd.DataFrame(),
            "final_capital": self.account.equity,
            "total_return": (self.account.equity - self.account.initial_cash) / self.account.initial_cash,
            "latency_stats": self.latency.all_stats(),
            "order_stats": self.order_manager.stats(),
        }

    def _process_tick(self, row: pd.Series):
        ts = row.get("timestamp", datetime.now(timezone.utc))
        symbol = row.get("symbol", "THYAO")
        price = row["price"]
        size = row.get("size", 0.0)
        bid = row.get("bid", price)
        ask = row.get("ask", price)

        # Ingest tick
        self.aggregator.ingest_tick(symbol, ts, price, size)

        # Check if bar completed
        bars = self.aggregator.flush_bars()
        if symbol in bars and not bars[symbol].empty:
            self._on_bar(symbol, bars[symbol].iloc[-1], bid, ask)

        # Check existing positions for SL/TP
        self._check_exits(symbol, price)

        self.equity_curve.append((ts, self.account.equity))

    def _on_bar(self, symbol: str, bar: pd.Series, bid: float, ask: float):
        self._bar_counter += 1
        if self._bar_counter < 30:
            return  # Need warmup

        # Generate signal from single-symbol bars
        df = self.aggregator.get_bars(symbol)
        if df.empty or len(df) < 30:
            return

        signal = generate_signal_from_df(df, strategy=self.strategy)
        if signal is None or signal["signal"] == 0:
            return

        side = "BUY" if signal["signal"] == 1 else "SELL"
        entry = signal["entry"]

        # Risk filter
        self.latency.start_timer("risk")
        risk_result = self.risk.check(
            symbol=symbol,
            bid=bid,
            ask=ask,
            equity=self.account.equity,
            open_position_count=self.account.open_position_count,
            proposed_size=100,  # Base size; adjusted by risk
            side=side,
        )
        self.latency.stop_timer("risk")

        if not risk_result.allowed:
            return

        size = risk_result.adjusted_size if risk_result.adjusted_size > 0 else 100

        # Order lifecycle simulation
        order_id = f"hft_{self._bar_counter}"
        order = self.order_manager.create_order(order_id, symbol, side, size, entry)
        self.order_manager.submit(order_id)

        # Fill simulation
        if self.fill_model.can_fill(entry, side, size):
            fill_price = self.fill_model.fill_price(entry, side, size)
            comm = self.commission.calculate(fill_price, size)

            self.order_manager.fill(order_id, size, fill_price)

            if side == "BUY":
                self.pos_manager.enter_position(symbol, size, fill_price, comm["total"])
            else:
                self.pos_manager.exit_position(symbol, size, fill_price, comm["total"])

            self.risk.record_trade()

    def _check_exits(self, symbol: str, price: float):
        pos = self.account.get_position(symbol)
        if pos is None or not pos.is_open:
            return

        should_exit, reason = self.pos_manager.can_exit(symbol, price, sl_pct=0.002, tp_pct=0.005)
        if should_exit:
            self._exit(symbol, pos.quantity, price, reason)

    def _exit(self, symbol: str, qty: float, price: float, reason: str):
        order_id = f"hft_exit_{symbol}_{reason}"
        order = self.order_manager.create_order(order_id, symbol, "SELL", qty, price)
        self.order_manager.submit(order_id)

        if self.fill_model.can_fill(price, "SELL", qty):
            fill_price = self.fill_model.fill_price(price, "SELL", qty)
            comm = self.commission.calculate(fill_price, qty)
            self.order_manager.fill(order_id, qty, fill_price)
            pnl = self.pos_manager.exit_position(symbol, qty, fill_price, comm["total"])

            self.trades.append({
                "symbol": symbol,
                "exit_price": fill_price,
                "size": qty,
                "reason": reason,
                "pnl": pnl,
                "commission": comm["total"],
            })
