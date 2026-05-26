"""
ms_strategy.py — Millisecond Order-Flow Imbalance Strategy

Simulated millisecond-level scalping using bid/ask imbalance
and micro-bar momentum. Designed for BIST where true sub-second
execution is limited; uses 500ms-3s synthetic bars from tick feed.

Target: 0.01-0.05% per trade, hold 500ms-3s.
Max agents: 1 (solo speed runner).

Usage:
    from strategy.gold_mining.ms_strategy import MSStrategy
    strategy = MSStrategy()
    signal = strategy.generate(tick_stream)
"""

import numpy as np
from typing import Optional, Dict


class MSStrategy:
    """
    Millisecond scalper based on order-flow imbalance.

    Uses synthetic 500ms micro-bars computed from tick stream.
    Signal triggers on bid/ask imbalance + micro-momentum.
    """

    def __init__(
        self,
        imbalance_threshold: float = 0.6,   # Bid/ask ratio threshold
        min_volume: int = 10,              # Minimum shares in bar
        max_spread_pct: float = 0.001,     # 0.1% max spread
        profit_target_pct: float = 0.03,   # Target 0.03%
        stop_loss_pct: float = 0.01,      # SL 0.01%
    ):
        self.imbalance_threshold = imbalance_threshold
        self.min_volume = min_volume
        self.max_spread_pct = max_spread_pct
        self.profit_target_pct = profit_target_pct
        self.stop_loss_pct = stop_loss_pct

    def generate(self, micro_bar: dict) -> Optional[dict]:
        """
        Generate signal from a single synthetic micro-bar.
        micro_bar: {
            "timestamp", "open", "high", "low", "close",
            "bid_volume", "ask_volume", "total_volume"
        }
        Returns: signal dict or None.
        """
        bid_vol = micro_bar.get("bid_volume", 0)
        ask_vol = micro_bar.get("ask_volume", 0)
        total_vol = micro_bar.get("total_volume", 0)
        price = micro_bar["close"]
        spread = micro_bar.get("spread", 0)

        if total_vol < self.min_volume:
            return None

        # Spread check
        if price > 0 and (spread / price) > self.max_spread_pct:
            return None

        # Order-flow imbalance
        if bid_vol + ask_vol == 0:
            return None
        imbalance = bid_vol / (bid_vol + ask_vol)

        # Micro-momentum: close near high (buy pressure) or low (sell pressure)
        o = micro_bar["open"]
        h = micro_bar["high"]
        l = micro_bar["low"]
        c = micro_bar["close"]

        if o == 0:
            return None
        body = (c - o) / o

        if imbalance > self.imbalance_threshold and body > 0:
            # Strong bid pressure + bullish micro-bar
            return self._signal("BUY", price, micro_bar["timestamp"])
        elif imbalance < (1.0 - self.imbalance_threshold) and body < 0:
            # Strong ask pressure + bearish micro-bar
            return self._signal("SELL", price, micro_bar["timestamp"])
        return None

    def _signal(self, side: str, price: float, timestamp) -> dict:
        sl = price * (1.0 - self.stop_loss_pct) if side == "BUY" else price * (1.0 + self.stop_loss_pct)
        tp = price * (1.0 + self.profit_target_pct) if side == "BUY" else price * (1.0 - self.profit_target_pct)
        return {
            "side": side,
            "entry": price,
            "sl": round(sl, 4),
            "tp": round(tp, 4),
            "strategy": "MS_ORDER_FLOW",
            "timestamp": timestamp,
            "expected_profit_pct": self.profit_target_pct,
            "max_loss_pct": self.stop_loss_pct,
            "holding_seconds": (0.5, 3.0),
        }

    def batch_generate(self, micro_bars: list[dict]) -> list[dict]:
        """Generate signals from a list of micro-bars."""
        signals = []
        for bar in micro_bars:
            sig = self.generate(bar)
            if sig:
                signals.append(sig)
        return signals
