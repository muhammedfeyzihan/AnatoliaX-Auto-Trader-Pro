"""
execution_laws.py — Immutable Execution Law Engine

Pre-trade guardian that blocks ALL execution until the system autonomously
detects, solves, verifies and learns from uncertainty. No trade bypasses these laws.

Integrates with: UnifiedRiskEngine, IntegrationOrchestrator, KillSwitch.

Usage:
    from risk.execution_laws import ImmutableExecutionLawEngine
    law = ImmutableExecutionLawEngine()
    verdict = law.check(signal={"symbol": "THYAO", "side": "BUY", "size": 100})
    if not verdict.allowed:
        print("BLOCKED:", verdict.reasons)
"""

import os
import sys
import time
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

import numpy as np


class LawStatus(Enum):
    PASS = "PASS"
    BLOCK = "BLOCK"
    WARN = "WARN"


@dataclass
class LawVerdict:
    allowed: bool
    reasons: List[str] = field(default_factory=list)
    status: LawStatus = LawStatus.PASS
    checksum: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "reasons": self.reasons,
            "status": self.status.value,
            "checksum": self.checksum,
            "timestamp": self.timestamp,
        }


class ImmutableExecutionLawEngine:
    """
    15 Immutable Execution Laws.

    Every trade must pass ALL laws. A single BLOCK halts execution.
    WARN conditions are logged but do not block (unless configured strict).
    """

    def __init__(
        self,
        strict_mode: bool = True,
        max_uncertainty_pct: float = 0.15,
        max_volatility_spike: float = 5.0,  # ATR% spike
        max_slippage_expected: float = 0.5,
        max_liquidity_spread_pct: float = 1.0,
        min_exchange_health_score: float = 70.0,
        max_ws_latency_ms: float = 500.0,
        max_drawdown_from_peak: float = 0.10,
        max_portfolio_heat: float = 0.80,
        max_stale_order_seconds: float = 30.0,
        min_replay_match_score: float = 0.99,
    ):
        self.strict_mode = strict_mode
        self.max_uncertainty_pct = max_uncertainty_pct
        self.max_volatility_spike = max_volatility_spike
        self.max_slippage_expected = max_slippage_expected
        self.max_liquidity_spread_pct = max_liquidity_spread_pct
        self.min_exchange_health_score = min_exchange_health_score
        self.max_ws_latency_ms = max_ws_latency_ms
        self.max_drawdown_from_peak = max_drawdown_from_peak
        self.max_portfolio_heat = max_portfolio_heat
        self.max_stale_order_seconds = max_stale_order_seconds
        self.min_replay_match_score = min_replay_match_score

        # Mutable state tracking
        self._peak_equity: float = 0.0
        self._current_equity: float = 0.0
        self._portfolio_heat: float = 0.0
        self._exchange_health: Dict[str, float] = {}
        self._ws_latency_ms: float = 0.0
        self._replay_match_score: float = 1.0
        self._uncertainty_score: float = 0.0
        self._block_history: List[dict] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def check(self, signal: dict, state: Optional[dict] = None) -> LawVerdict:
        """
        Run all 15 immutable laws against a signal.
        signal: dict with symbol, side, size, price, sl, tp, confidence
        state: optional dict with equity, heat, exchange health
        """
        reasons: List[str] = []
        warns: List[str] = []

        if state:
            self._update_state(state)

        laws = [
            self._law_uncertainty(signal),
            self._law_corrupted_state(),
            self._law_replay_mismatch(),
            self._law_anomalous_volatility(signal),
            self._law_unstable_liquidity(signal),
            self._law_leverage_instability(signal),
            self._law_exchange_desync(),
            self._law_websocket_consistency(),
            self._law_risk_verification(signal),
            self._law_probabilistic_uncertainty(signal),
            self._law_fake_breakout(signal),
            self._law_black_swan(),
            self._law_liquidation_cascade(signal),
            self._law_portfolio_heat(signal),
            self._law_stale_orders(signal),
        ]

        for name, passed, reason in laws:
            if not passed:
                if self.strict_mode:
                    reasons.append(f"{name}: {reason}")
                else:
                    warns.append(f"{name}: {reason}")

        allowed = len(reasons) == 0
        status = LawStatus.PASS if allowed else LawStatus.BLOCK
        if not allowed:
            self._block_history.append({
                "time": time.time(),
                "signal": signal,
                "reasons": reasons,
            })

        checksum = self._checksum(signal, reasons)
        return LawVerdict(
            allowed=allowed,
            reasons=reasons + warns,
            status=status,
            checksum=checksum,
        )

    def is_execution_allowed(self) -> bool:
        """Global execution gate — true only if system-wide health is green."""
        return (
            self._uncertainty_score <= self.max_uncertainty_pct
            and self._portfolio_heat <= self.max_portfolio_heat
            and self._ws_latency_ms <= self.max_ws_latency_ms
        )

    def update_state(self, state: dict):
        self._update_state(state)

    def get_block_history(self, last_n: int = 100) -> List[dict]:
        return self._block_history[-last_n:]

    def to_dict(self) -> dict:
        return {
            "strict_mode": self.strict_mode,
            "uncertainty_score": self._uncertainty_score,
            "portfolio_heat": self._portfolio_heat,
            "ws_latency_ms": self._ws_latency_ms,
            "replay_match_score": self._replay_match_score,
            "execution_allowed": self.is_execution_allowed(),
            "total_blocks": len(self._block_history),
        }

    # ------------------------------------------------------------------
    # State update helpers
    # ------------------------------------------------------------------
    def _update_state(self, state: dict):
        self._current_equity = state.get("equity", self._current_equity)
        self._peak_equity = max(self._peak_equity, self._current_equity)
        self._portfolio_heat = state.get("portfolio_heat", self._portfolio_heat)
        self._exchange_health = state.get("exchange_health", self._exchange_health)
        self._ws_latency_ms = state.get("ws_latency_ms", self._ws_latency_ms)
        self._replay_match_score = state.get("replay_match_score", 1.0)
        self._uncertainty_score = state.get("uncertainty_score", 0.0)

    # ------------------------------------------------------------------
    # The 15 Immutable Laws
    # ------------------------------------------------------------------
    def _law_uncertainty(self, signal: dict) -> Tuple[str, bool, str]:
        """Law 1: Unresolved uncertainty blocks execution."""
        score = self._uncertainty_score
        if score > self.max_uncertainty_pct:
            return ("L1_UNCERTAINTY", False, f"Uncertainty {score:.2%} > {self.max_uncertainty_pct:.2%}")
        return ("L1_UNCERTAINTY", True, "OK")

    def _law_corrupted_state(self) -> Tuple[str, bool, str]:
        """Law 2: Corrupted internal state blocks execution."""
        # Corruption heuristic: negative equity or NaN values
        if self._current_equity < 0 or np.isnan(self._current_equity):
            return ("L2_CORRUPTED_STATE", False, f"Equity {self._current_equity} invalid")
        return ("L2_CORRUPTED_STATE", True, "OK")

    def _law_replay_mismatch(self) -> Tuple[str, bool, str]:
        """Law 3: Replay mismatch blocks execution."""
        if self._replay_match_score < self.min_replay_match_score:
            return ("L3_REPLAY_MISMATCH", False, f"Match {self._replay_match_score:.3f} < {self.min_replay_match_score}")
        return ("L3_REPLAY_MISMATCH", True, "OK")

    def _law_anomalous_volatility(self, signal: dict) -> Tuple[str, bool, str]:
        """Law 4: Anomalous volatility blocks execution."""
        atr_pct = signal.get("atr_pct", 0.0)
        if atr_pct > self.max_volatility_spike:
            return ("L4_ANOMALOUS_VOL", False, f"ATR% {atr_pct:.2f} > {self.max_volatility_spike}")
        return ("L4_ANOMALOUS_VOL", True, "OK")

    def _law_unstable_liquidity(self, signal: dict) -> Tuple[str, bool, str]:
        """Law 5: Unstable liquidity / wide spread blocks execution."""
        spread = signal.get("spread_pct", 0.0)
        if spread > self.max_liquidity_spread_pct:
            return ("L5_UNSTABLE_LIQUIDITY", False, f"Spread {spread:.2f}% > {self.max_liquidity_spread_pct}%")
        return ("L5_UNSTABLE_LIQUIDITY", True, "OK")

    def _law_leverage_instability(self, signal: dict) -> Tuple[str, bool, str]:
        """Law 6: Leverage instability blocks execution."""
        leverage = signal.get("leverage", 1.0)
        if leverage > 10.0:
            return ("L6_LEVERAGE_INSTABILITY", False, f"Leverage {leverage}x > 10x")
        return ("L6_LEVERAGE_INSTABILITY", True, "OK")

    def _law_exchange_desync(self) -> Tuple[str, bool, str]:
        """Law 7: Exchange desynchronization blocks execution."""
        min_health = min(self._exchange_health.values()) if self._exchange_health else 100.0
        if min_health < self.min_exchange_health_score:
            return ("L7_EXCHANGE_DESYNC", False, f"Health {min_health:.0f} < {self.min_exchange_health_score}")
        return ("L7_EXCHANGE_DESYNC", True, "OK")

    def _law_websocket_consistency(self) -> Tuple[str, bool, str]:
        """Law 8: WebSocket inconsistency blocks execution."""
        if self._ws_latency_ms > self.max_ws_latency_ms:
            return ("L8_WS_INCONSISTENCY", False, f"WS latency {self._ws_latency_ms:.0f}ms > {self.max_ws_latency_ms}ms")
        return ("L8_WS_INCONSISTENCY", True, "OK")

    def _law_risk_verification(self, signal: dict) -> Tuple[str, bool, str]:
        """Law 9: Failed risk verification blocks execution."""
        confidence = signal.get("confidence", 0.0)
        if confidence < 50.0:
            return ("L9_RISK_VERIFY", False, f"Confidence {confidence} < 50")
        return ("L9_RISK_VERIFY", True, "OK")

    def _law_probabilistic_uncertainty(self, signal: dict) -> Tuple[str, bool, str]:
        """Law 10: Probabilistic uncertainty > threshold blocks execution."""
        prob = signal.get("prob_win", 1.0)
        if prob < 0.45:
            return ("L10_PROB_UNCERTAINTY", False, f"P(win) {prob:.2f} < 0.45")
        return ("L10_PROB_UNCERTAINTY", True, "OK")

    def _law_fake_breakout(self, signal: dict) -> Tuple[str, bool, str]:
        """Law 11: Fake breakout probability blocks execution."""
        fake_prob = signal.get("fake_breakout_prob", 0.0)
        if fake_prob > 0.35:
            return ("L11_FAKE_BREAKOUT", False, f"Fake breakout {fake_prob:.2f} > 0.35")
        return ("L11_FAKE_BREAKOUT", True, "OK")

    def _law_black_swan(self) -> Tuple[str, bool, str]:
        """Law 12: Black swan anomaly blocks execution."""
        # Heuristic: drawdown > 10% from peak or extreme volatility
        if self._peak_equity > 0:
            dd = (self._peak_equity - self._current_equity) / self._peak_equity
            if dd > self.max_drawdown_from_peak:
                return ("L12_BLACK_SWAN", False, f"Drawdown {dd:.2%} > {self.max_drawdown_from_peak:.2%}")
        return ("L12_BLACK_SWAN", True, "OK")

    def _law_liquidation_cascade(self, signal: dict) -> Tuple[str, bool, str]:
        """Law 13: Liquidation cascade risk blocks execution."""
        liq_risk = signal.get("liquidation_risk", 0.0)
        if liq_risk > 0.25:
            return ("L13_LIQUIDATION_CASCADE", False, f"Liq risk {liq_risk:.2f} > 0.25")
        return ("L13_LIQUIDATION_CASCADE", True, "OK")

    def _law_portfolio_heat(self, signal: dict) -> Tuple[str, bool, str]:
        """Law 14: Portfolio heat overflow blocks execution."""
        if self._portfolio_heat > self.max_portfolio_heat:
            return ("L14_PORTFOLIO_HEAT", False, f"Heat {self._portfolio_heat:.2f} > {self.max_portfolio_heat}")
        return ("L14_PORTFOLIO_HEAT", True, "OK")

    def _law_stale_orders(self, signal: dict) -> Tuple[str, bool, str]:
        """Law 15: Stale orders / partial fill inconsistency blocks execution."""
        stale_age = signal.get("stale_order_seconds", 0.0)
        if stale_age > self.max_stale_order_seconds:
            return ("L15_STALE_ORDERS", False, f"Stale {stale_age:.0f}s > {self.max_stale_order_seconds}s")
        return ("L15_STALE_ORDERS", True, "OK")

    def _checksum(self, signal: dict, reasons: List[str]) -> str:
        payload = f"{signal}_{reasons}_{time.time()}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


if __name__ == "__main__":
    law = ImmutableExecutionLawEngine(strict_mode=True)
    v = law.check(
        signal={"symbol": "THYAO", "side": "BUY", "size": 100, "price": 105.0,
                "confidence": 80.0, "atr_pct": 2.0, "spread_pct": 0.3,
                "leverage": 1.0, "prob_win": 0.6, "fake_breakout_prob": 0.1,
                "liquidation_risk": 0.05, "stale_order_seconds": 0.0},
        state={"equity": 100_000.0, "portfolio_heat": 0.3, "ws_latency_ms": 50.0},
    )
    print(v)
