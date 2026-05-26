"""
risk_filter.py — HFT-specific risk controls.
Spread filter, slippage guard, rate limiter, inventory skew.
"""

import time
from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class RiskFilterResult:
    allowed: bool
    reason: str = ""
    adjusted_size: float = 0.0


class RiskFilter:
    """
    High-speed risk gate for HFT.
    All checks must complete in < 1ms.
    """

    def __init__(
        self,
        max_positions: int = 3,
        max_trades_per_minute: int = 10,
        max_daily_trades: int = 50,
        max_position_value_pct: float = 0.005,
        max_spread_pct: float = 0.003,
        max_slippage_pct: float = 0.002,
        commission_rate: float = 0.001,
        bsmv_rate: float = 0.001,
        min_profit_target_pct: float = 0.003,
    ):
        self.max_positions = max_positions
        self.max_trades_per_minute = max_trades_per_minute
        self.max_daily_trades = max_daily_trades
        self.max_position_value_pct = max_position_value_pct
        self.max_spread_pct = max_spread_pct
        self.max_slippage_pct = max_slippage_pct
        self.commission_rate = commission_rate
        self.bsmv_rate = bsmv_rate
        self.min_profit_target_pct = min_profit_target_pct

        self._trade_log: list = []  # timestamps of recent trades
        self._open_count: int = 0

    def _is_rate_limited(self) -> bool:
        now = time.time()
        cutoff = now - 60.0
        self._trade_log = [t for t in self._trade_log if t >= cutoff]
        return len(self._trade_log) >= self.max_trades_per_minute

    def _daily_limit_reached(self) -> bool:
        # Simplified: use today's count (would be persisted in real impl)
        return len(self._trade_log) >= self.max_daily_trades

    def check(
        self,
        symbol: str,
        bid: float,
        ask: float,
        equity: float,
        open_position_count: int,
        proposed_size: float,
        side: str = "BUY",
    ) -> RiskFilterResult:
        """Run all risk checks. Returns RiskFilterResult."""

        # Spread check
        if bid > 0 and ask > 0:
            spread = (ask - bid) / ((ask + bid) / 2.0)
            if spread > self.max_spread_pct:
                return RiskFilterResult(False, f"Spread too wide: {spread:.4f}")

        # Position count
        if open_position_count >= self.max_positions:
            return RiskFilterResult(False, "Max positions reached")

        # Rate limit
        if self._is_rate_limited():
            return RiskFilterResult(False, "Trade rate limit exceeded")

        if self._daily_limit_reached():
            return RiskFilterResult(False, "Daily trade limit reached")

        # Position size vs equity
        notional = proposed_size * (ask if side == "BUY" else bid)
        if notional > equity * self.max_position_value_pct:
            adjusted = int((equity * self.max_position_value_pct) / (ask if side == "BUY" else bid))
            if adjusted <= 0:
                return RiskFilterResult(False, "Position size too small after adjustment")
            return RiskFilterResult(True, "Size adjusted", adjusted_size=float(adjusted))

        # Profit feasibility: min profit must cover commission + slippage
        total_cost = self.commission_rate + self.bsmv_rate + self.max_slippage_pct
        if self.min_profit_target_pct <= total_cost:
            return RiskFilterResult(
                False,
                f"Min profit {self.min_profit_target_pct:.4f} <= total cost {total_cost:.4f}"
            )

        return RiskFilterResult(True, "OK", adjusted_size=proposed_size)

    def record_trade(self):
        """Record a trade for rate limiting."""
        self._trade_log.append(time.time())
        self._open_count += 1

    def record_close(self):
        self._open_count = max(0, self._open_count - 1)
