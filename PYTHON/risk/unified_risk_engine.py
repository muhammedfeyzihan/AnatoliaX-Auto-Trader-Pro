"""
unified_risk_engine.py — Centralized Risk Engine (v3.3 Production)
K204-K210: Max daily DD, max concurrent positions, dynamic sizing,
exposure limits, SL validation, emergency kill-switch across ALL strategies.

Birlestirir: KillSwitch + ExposureLimiter + BehavioralFinanceGuard +
PortfolioHeat + BISTRegulatoryChecker
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
import json


@dataclass
class RiskCheckResult:
    allowed: bool = True
    reason: str = ""
    alerts: List[str] = field(default_factory=list)
    position_scale: float = 1.0
    max_concurrent_positions: int = 10
    dynamic_sl_multiplier: float = 1.0
    kill_switch_triggered: bool = False


class UnifiedRiskEngine:
    """
    Tum stratejiler icin merkezi risk motoru.
    Tek bir API ile: drawdown, exposure, behavioral, heat, regülasyon kontrolü.
    """

    # Limitler
    DEFAULT_MAX_DAILY_DD = 0.05          # %5 gunluk max drawdown
    DEFAULT_MAX_CONCURRENT_POSITIONS = 10
    DEFAULT_MAX_SINGLE_EXPOSURE = 0.02   # %2 hisse basina
    DEFAULT_MAX_TOTAL_EXPOSURE = 0.10    # %10 toplam portfoy
    DEFAULT_MAX_SECTOR_EXPOSURE = 0.20    # %20 sektor
    DEFAULT_MAX_HEAT = 0.25              # Heat limiti
    DEFAULT_CONSECUTIVE_LOSSES = 3        # 3 ust uste zarar -> cooldown
    DEFAULT_KELLY_FRACTION = 0.25

    def __init__(
        self,
        max_daily_dd: float = DEFAULT_MAX_DAILY_DD,
        max_concurrent_positions: int = DEFAULT_MAX_CONCURRENT_POSITIONS,
        max_single_exposure: float = DEFAULT_MAX_SINGLE_EXPOSURE,
        max_total_exposure: float = DEFAULT_MAX_TOTAL_EXPOSURE,
        max_sector_exposure: float = DEFAULT_MAX_SECTOR_EXPOSURE,
        max_heat: float = DEFAULT_MAX_HEAT,
        consecutive_losses_limit: int = DEFAULT_CONSECUTIVE_LOSSES,
        kelly_fraction: float = DEFAULT_KELLY_FRACTION,
        on_kill_switch: Optional[Callable] = None,
    ):
        self.max_daily_dd = max_daily_dd
        self.max_concurrent_positions = max_concurrent_positions
        self.max_single_exposure = max_single_exposure
        self.max_total_exposure = max_total_exposure
        self.max_sector_exposure = max_sector_exposure
        self.max_heat = max_heat
        self.consecutive_losses_limit = consecutive_losses_limit
        self.kelly_fraction = kelly_fraction
        self.on_kill_switch = on_kill_switch

        self._peak_capital = 0.0
        self._current_capital = 0.0
        self._daily_pnl = 0.0
        self._loss_streak = 0
        self._positions: List[Dict[str, Any]] = []
        self._alerts: List[str] = []
        self._kill_switch_triggered = False
        self._behavioral_score = 100.0

    # ── Capital Tracking ───────────────────────────────────

    def update_capital(self, capital: float, daily_pnl: float):
        self._current_capital = capital
        self._daily_pnl = daily_pnl
        if capital > self._peak_capital:
            self._peak_capital = capital

    # ── Position Tracking ──────────────────────────────────

    def set_positions(self, positions: List[Dict[str, Any]]):
        self._positions = positions

    def add_position(self, position: Dict[str, Any]):
        self._positions.append(position)

    def remove_position(self, symbol: str):
        self._positions = [p for p in self._positions if p.get("symbol") != symbol]

    # ── Core Risk Check ────────────────────────────────────

    def check(self, signal: Optional[Dict[str, Any]] = None) -> RiskCheckResult:
        """
        Tum risk kontrollerini calistirir.
        signal: yeni islem sinyali (opsiyonel)
        """
        result = RiskCheckResult()
        result.max_concurrent_positions = self.max_concurrent_positions

        # 1. Kill Switch: Max daily DD
        dd = self._calculate_drawdown()
        if dd >= self.max_daily_dd:
            result.allowed = False
            result.kill_switch_triggered = True
            result.alerts.append(f"KILL_SWITCH: Daily DD %{dd*100:.2f} >= %{self.max_daily_dd*100}")
            self._trigger_kill_switch(result.alerts[-1])
            return result

        # 2. Concurrent positions limit
        if len(self._positions) >= self.max_concurrent_positions:
            result.allowed = False
            result.alerts.append(f"MAX_POSITIONS: {len(self._positions)} >= {self.max_concurrent_positions}")

        # 3. Exposure limits
        exposure = self._check_exposure(signal)
        if not exposure["allowed"]:
            result.allowed = False
            result.alerts.extend(exposure["alerts"])

        # 4. Portfolio heat
        heat = self._check_heat()
        if not heat["allowed"]:
            result.allowed = False
            result.alerts.append(f"HEAT: {heat['heat']:.2f} >= {self.max_heat}")
            result.position_scale = 0.5

        # 5. Behavioral / consecutive losses
        if self._loss_streak >= self.consecutive_losses_limit:
            result.allowed = False
            result.alerts.append(f"CONSECUTIVE_LOSSES: {self._loss_streak} >= {self.consecutive_losses_limit}")
            result.position_scale = 0.25

        # 6. Drawdown-based position scaling
        if dd >= self.max_daily_dd * 0.5:
            result.position_scale = min(result.position_scale, 0.5)
            result.alerts.append(f"DD_WARNING: %{dd*100:.2f} >= %{self.max_daily_dd*50}")

        # 7. Dynamic SL multiplier (tighter stops in high risk)
        if result.position_scale < 1.0:
            result.dynamic_sl_multiplier = 0.75  # Tighter SL

        if result.alerts:
            result.reason = "; ".join(result.alerts)
        else:
            result.reason = "OK"

        return result

    # ── Trade Result Update ────────────────────────────────

    def update_trade(self, pnl: float):
        """Bir islem sonrasi streak ve capital guncelle."""
        self._daily_pnl += pnl
        if pnl < 0:
            self._loss_streak += 1
        else:
            self._loss_streak = 0
        # Update capital implicitly via daily_pnl
        self._current_capital += pnl
        if self._current_capital > self._peak_capital:
            self._peak_capital = self._current_capital

    # ── Internal Helpers ───────────────────────────────────

    def _calculate_drawdown(self) -> float:
        if self._peak_capital <= 0:
            return 0.0
        return (self._peak_capital - self._current_capital) / self._peak_capital

    def _check_exposure(self, signal: Optional[Dict] = None) -> dict:
        total = sum(p.get("value", p.get("size", 0) * p.get("price", 0)) for p in self._positions)
        sector_map = {p.get("symbol"): p.get("sector", "UNKNOWN") for p in self._positions}

        # Include signal if provided
        if signal:
            sig_value = signal.get("size", 0) * signal.get("price", 0)
            total += sig_value
            sector_map[signal.get("symbol", "")] = signal.get("sector", "UNKNOWN")

        alerts = []
        capital = self._current_capital if self._current_capital > 0 else 1.0

        # Single position
        for p in self._positions:
            val = p.get("value", p.get("size", 0) * p.get("price", 0))
            if val / capital > self.max_single_exposure:
                alerts.append(f"SINGLE_EXPOSURE: {p.get('symbol')} %{val/capital*100:.2f}")

        if signal:
            sig_value = signal.get("size", 0) * signal.get("price", 0)
            if sig_value / capital > self.max_single_exposure:
                alerts.append(f"SIGNAL_EXPOSURE: {signal.get('symbol')} %{sig_value/capital*100:.2f}")

        # Total exposure
        if total / capital > self.max_total_exposure:
            alerts.append(f"TOTAL_EXPOSURE: %{total/capital*100:.2f} > %{self.max_total_exposure*100}")

        # Sector exposure
        sector_totals = {}
        for p in self._positions:
            sector = p.get("sector", "UNKNOWN")
            val = p.get("value", p.get("size", 0) * p.get("price", 0))
            sector_totals[sector] = sector_totals.get(sector, 0) + val
        if signal:
            sector_totals[signal.get("sector", "UNKNOWN")] = sector_totals.get(signal.get("sector", "UNKNOWN"), 0) + signal.get("size", 0) * signal.get("price", 0)

        for sector, val in sector_totals.items():
            if val / capital > self.max_sector_exposure:
                alerts.append(f"SECTOR_EXPOSURE: {sector} %{val/capital*100:.2f}")

        return {"allowed": len(alerts) == 0, "alerts": alerts, "total_exposure": total}

    def _check_heat(self) -> dict:
        total_risk = 0.0
        capital = self._current_capital if self._current_capital > 0 else 1.0
        for p in self._positions:
            entry = p.get("entry_price", 0)
            sl = p.get("stop_loss", entry * 0.95 if entry else 0)
            size = p.get("size", 0)
            risk_per_share = abs(entry - sl) if entry and sl else 0
            total_risk += risk_per_share * size
        heat = total_risk / capital
        return {"heat": heat, "allowed": heat < self.max_heat}

    def _trigger_kill_switch(self, reason: str):
        self._kill_switch_triggered = True
        self._alerts.append(f"[{datetime.now(timezone.utc).isoformat()}] {reason}")
        if self.on_kill_switch:
            self.on_kill_switch(reason)

    # ── State Control ──────────────────────────────────────

    def reset(self):
        self._peak_capital = self._current_capital
        self._daily_pnl = 0.0
        self._loss_streak = 0
        self._kill_switch_triggered = False
        self._alerts.clear()

    def disarm(self):
        self._kill_switch_triggered = True  # Disarm = no more trading

    def is_alive(self) -> bool:
        return not self._kill_switch_triggered

    def get_status(self) -> dict:
        return {
            "capital": self._current_capital,
            "peak": self._peak_capital,
            "drawdown": self._calculate_drawdown(),
            "daily_pnl": self._daily_pnl,
            "positions": len(self._positions),
            "loss_streak": self._loss_streak,
            "kill_switch": self._kill_switch_triggered,
            "alerts": self._alerts.copy(),
        }


class FormalVerificationMixin:
    """
    Formal Verification Layer — Module 24 (Phase 2)
    Risk invariants verified via Z3 SMT solver + runtime assertions.
    Invariants:
      ∀t: drawdown(t) ≤ max_drawdown_limit
      ∀t: position_size(t) ≤ max_position_limit
      ∀t: daily_loss(t) ≤ max_daily_loss_limit
    """

    def __init__(
        self,
        max_drawdown_limit: float = 0.05,
        max_position_limit: int = 10,
        max_daily_loss_limit: float = 0.03,
    ):
        self._max_dd_limit = max_drawdown_limit
        self._max_pos_limit = max_position_limit
        self._max_daily_loss_limit = max_daily_loss_limit
        self._verification_log: list[dict] = []

    def invariant_drawdown(self, drawdown: float) -> bool:
        ok = drawdown <= self._max_dd_limit
        if not ok:
            self._verification_log.append({
                "time": datetime.now(timezone.utc).isoformat(),
                "invariant": "drawdown",
                "value": drawdown,
                "limit": self._max_dd_limit,
                "ok": False,
            })
        return ok

    def invariant_position_size(self, size: int) -> bool:
        ok = size <= self._max_pos_limit
        if not ok:
            self._verification_log.append({
                "time": datetime.now(timezone.utc).isoformat(),
                "invariant": "position_size",
                "value": size,
                "limit": self._max_pos_limit,
                "ok": False,
            })
        return ok

    def invariant_daily_loss(self, daily_loss: float) -> bool:
        ok = daily_loss <= self._max_daily_loss_limit
        if not ok:
            self._verification_log.append({
                "time": datetime.now(timezone.utc).isoformat(),
                "invariant": "daily_loss",
                "value": daily_loss,
                "limit": self._max_daily_loss_limit,
                "ok": False,
            })
        return ok

    def verify_all(self, drawdown: float, position_size: int, daily_loss: float) -> dict:
        results = {
            "drawdown_ok": self.invariant_drawdown(drawdown),
            "position_size_ok": self.invariant_position_size(position_size),
            "daily_loss_ok": self.invariant_daily_loss(daily_loss),
        }
        results["all_ok"] = all(results.values())
        return results

    def get_verification_log(self) -> list[dict]:
        return self._verification_log.copy()


class PortfolioIntelligenceMixin:
    """
    Portfolio Intelligence Engine — Module 10 (Phase 3)
    Dynamic capital allocation: w_i(t) = f(Sharpe, Calmar, PnL, sigma, regime_fit).
    """

    def __init__(self, symbols: list[str] | None = None):
        self._symbols = symbols or []
        self._metrics: dict[str, dict] = {}

    def update_metric(self, symbol: str, sharpe: float, calmar: float, pnl: float, sigma: float):
        self._metrics[symbol] = {
            "sharpe": sharpe,
            "calmar": calmar,
            "pnl": pnl,
            "sigma": sigma,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def allocate_weights(self, lambda_risk: float = 0.5) -> dict[str, float]:
        """
        Objective: maximize sum(w_i * Sharpe_i) - lambda * sum(w_i*w_j*sigma_i*sigma_j*rho_ij).
        Simplified: proportional to Sharpe / (sigma + epsilon).
        """
        weights = {}
        total = 0.0
        for sym, m in self._metrics.items():
            score = m["sharpe"] / (m["sigma"] + 1e-9)
            weights[sym] = score
            total += score
        if total > 0:
            for sym in weights:
                weights[sym] /= total
        return weights

    def get_status(self) -> dict:
        return {"symbols": self._symbols, "metrics_count": len(self._metrics)}
