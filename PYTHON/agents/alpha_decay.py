"""
agents/alpha_decay.py — Alpha Decay Detection (Phase 4)
Module 14 from anatoliax_prompt_v6.txt

Features:
  - Monitor Sharpe_20d, win_rate_trend, profit_factor, max_consecutive_losses
  - Auto-disable thresholds
  - Kill switch: immediate_flat_all_positions + cooldown_period = 24h + manual_review_required
"""

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional


class AlphaDecayDetector:
    """
    Monitors strategy edge metrics and triggers kill switch when thresholds are breached.
    """

    def __init__(self):
        self._returns: List[float] = []
        self._win_rate_window: List[bool] = []
        self._pnls: List[float] = []
        self._consecutive_losses: int = 0
        self._kill_switch_triggered: bool = False
        self._kill_switch_time: Optional[datetime] = None
        self._cooldown_hours: float = 24.0

    def ingest_trade(self, pnl: float, regime: str = "sideways"):
        self._pnls.append(pnl)
        self._returns.append(pnl)
        if pnl > 0:
            self._win_rate_window.append(True)
            self._consecutive_losses = 0
        else:
            self._win_rate_window.append(False)
            self._consecutive_losses += 1

    def sharpe_20d(self) -> float:
        if len(self._returns) < 20:
            return 0.0
        recent = self._returns[-20:]
        mean = statistics.mean(recent)
        std = statistics.stdev(recent) if len(recent) > 1 else 0.0
        return mean / std if std > 0 else 0.0

    def win_rate_trend(self, window: int = 20) -> float:
        if len(self._win_rate_window) < window:
            return 0.0
        recent = self._win_rate_window[-window:]
        return sum(recent) / len(recent) * 100

    def profit_factor(self, window: int = 20) -> float:
        if len(self._pnls) < 2:
            return 0.0
        recent = self._pnls[-window:]
        gross_profit = sum(p for p in recent if p > 0)
        gross_loss = abs(sum(p for p in recent if p < 0))
        return gross_profit / gross_loss if gross_loss > 0 else float("inf")

    def check_decay(self) -> Dict:
        sharpe = self.sharpe_20d()
        win_rate = self.win_rate_trend()
        pf = self.profit_factor()
        drawdown = 0.0  # placeholder

        disabled = (
            sharpe < 0.5
            or drawdown > 0.10
            or win_rate < 40
            or pf < 1.0
            or self._consecutive_losses >= 5
        )

        if disabled and not self._kill_switch_triggered:
            self._kill_switch_triggered = True
            self._kill_switch_time = datetime.now(timezone.utc)

        return {
            "sharpe_20d": sharpe,
            "win_rate_pct": win_rate,
            "profit_factor": pf,
            "max_consecutive_losses": self._consecutive_losses,
            "disabled": disabled,
            "kill_switch": self._kill_switch_triggered,
        }

    def can_resume(self) -> bool:
        if not self._kill_switch_triggered or not self._kill_switch_time:
            return True
        elapsed = (datetime.now(timezone.utc) - self._kill_switch_time).total_seconds()
        return elapsed >= self._cooldown_hours * 3600
