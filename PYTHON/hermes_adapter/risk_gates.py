"""
risk_gates.py — 10 Independent Risk Gates
Hermes Trader pattern: every order must pass 10 risk checks
before execution. Any single RED blocks the order.

Usage:
    from hermes_adapter.risk_gates import RiskGateEngine
    engine = RiskGateEngine()
    ok, reasons = engine.check_all(symbol="THYAO", size=100, price=105.0, side="BUY")
    if not ok:
        print("Blocked:", reasons)
"""

from dataclasses import dataclass
from typing import List, Tuple
from datetime import datetime, timedelta


@dataclass
class GateResult:
    name: str
    passed: bool
    reason: str


class RiskGateEngine:
    """
    10 independent risk gates.
    Order passes only if ALL gates pass.
    """

    def __init__(
        self,
        max_notional_per_trade: float = 2_000.0,
        max_daily_loss_pct: float = 3.0,
        max_correlation: float = 0.80,
        min_confidence: float = 60.0,
        cooldown_seconds: float = 300.0,
        max_daily_trades: int = 10,
        max_open_positions: int = 5,
        sl_required: bool = True,
        tp_required: bool = True,
        market_open_required: bool = True,
    ):
        self.max_notional = max_notional_per_trade
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_correlation = max_correlation
        self.min_confidence = min_confidence
        self.cooldown = cooldown_seconds
        self.max_daily_trades = max_daily_trades
        self.max_open_positions = max_open_positions
        self.sl_required = sl_required
        self.tp_required = tp_required
        self.market_open_required = market_open_required

        # State tracking
        self._trade_log: list = []
        self._daily_pnl: float = 0.0
        self._last_trade_time: datetime = datetime.min

    def check_all(
        self,
        symbol: str,
        size: float,
        price: float,
        side: str,
        confidence: float = 0.0,
        sl: float = 0.0,
        tp: float = 0.0,
        open_positions: int = 0,
        portfolio_value: float = 100_000.0,
    ) -> Tuple[bool, List[str]]:
        """Run all 10 gates. Returns (passed, [reasons for failures])."""
        notional = size * price
        reasons: List[str] = []

        gates = [
            self._gate_confidence(confidence),
            self._gate_notional(notional),
            self._gate_daily_loss(portfolio_value),
            self._gate_cooldown(),
            self._gate_daily_trade_limit(),
            self._gate_max_positions(open_positions),
            self._gate_sl(sl, side, price),
            self._gate_tp(tp, side, price),
            self._gate_market_open(),
            self._gate_symbol_allowed(symbol),
        ]

        passed = True
        for g in gates:
            if not g.passed:
                passed = False
                reasons.append(f"{g.name}: {g.reason}")

        return passed, reasons

    def record_trade(self, pnl: float = 0.0):
        """Record a trade for stateful gates."""
        self._trade_log.append(datetime.now())
        self._daily_pnl += pnl
        self._last_trade_time = datetime.now()

    def reset_daily(self):
        self._trade_log = [t for t in self._trade_log if t.date() == datetime.now().date()]
        self._daily_pnl = 0.0

    # --- Individual gates ---

    def _gate_confidence(self, confidence: float) -> GateResult:
        ok = confidence >= self.min_confidence
        return GateResult(
            "CONFIDENCE",
            ok,
            f"Confidence {confidence:.0f} >= {self.min_confidence}" if ok else f"Too low: {confidence:.0f}",
        )

    def _gate_notional(self, notional: float) -> GateResult:
        ok = notional <= self.max_notional
        return GateResult(
            "NOTIONAL",
            ok,
            f"Notional {notional:.0f} <= {self.max_notional}" if ok else f"Exceeds {self.max_notional}",
        )

    def _gate_daily_loss(self, portfolio_value: float) -> GateResult:
        limit = -portfolio_value * (self.max_daily_loss_pct / 100.0)
        ok = self._daily_pnl >= limit
        return GateResult(
            "DAILY_LOSS",
            ok,
            f"PnL {self._daily_pnl:.0f} >= {limit:.0f}" if ok else f"Daily loss limit: {self._daily_pnl:.0f}",
        )

    def _gate_cooldown(self) -> GateResult:
        if self._last_trade_time == datetime.min:
            return GateResult("COOLDOWN", True, "First trade")
        elapsed = (datetime.now() - self._last_trade_time).total_seconds()
        ok = elapsed >= self.cooldown
        return GateResult(
            "COOLDOWN",
            ok,
            f"Cooldown {elapsed:.0f}s >= {self.cooldown}s" if ok else f"Wait {self.cooldown - elapsed:.0f}s",
        )

    def _gate_daily_trade_limit(self) -> GateResult:
        today = datetime.now().date()
        count = sum(1 for t in self._trade_log if t.date() == today)
        ok = count < self.max_daily_trades
        return GateResult(
            "DAILY_TRADES",
            ok,
            f"Trades today {count} < {self.max_daily_trades}" if ok else f"Limit reached: {count}",
        )

    def _gate_max_positions(self, open_count: int) -> GateResult:
        ok = open_count < self.max_open_positions
        return GateResult(
            "MAX_POSITIONS",
            ok,
            f"Open {open_count} < {self.max_open_positions}" if ok else f"Max reached: {open_count}",
        )

    def _gate_sl(self, sl: float, side: str, price: float) -> GateResult:
        if not self.sl_required:
            return GateResult("SL", True, "Optional")
        has_sl = sl > 0
        if has_sl and side == "BUY":
            has_sl = sl < price
        elif has_sl and side == "SELL":
            has_sl = sl > price
        return GateResult("SL", has_sl, "Valid" if has_sl else "Missing or invalid")

    def _gate_tp(self, tp: float, side: str, price: float) -> GateResult:
        if not self.tp_required:
            return GateResult("TP", True, "Optional")
        has_tp = tp > 0
        if has_tp and side == "BUY":
            has_tp = tp > price
        elif has_tp and side == "SELL":
            has_tp = tp < price
        return GateResult("TP", has_tp, "Valid" if has_tp else "Missing or invalid")

    def _gate_market_open(self) -> GateResult:
        if not self.market_open_required:
            return GateResult("MARKET_OPEN", True, "Optional")
        try:
            from data.market_calendar import BISTCalendar
            cal = BISTCalendar()
            ok = cal.is_market_open()
            return GateResult("MARKET_OPEN", ok, "Open" if ok else cal.get_reason())
        except Exception:
            return GateResult("MARKET_OPEN", False, "Calendar check failed")

    def _gate_symbol_allowed(self, symbol: str) -> GateResult:
        # Blocklist / allowlist can be added here
        blocked = ["", "TEST", "MOCK"]
        ok = symbol.upper() not in blocked
        return GateResult("SYMBOL", ok, f"{symbol} allowed" if ok else "Blocked symbol")
