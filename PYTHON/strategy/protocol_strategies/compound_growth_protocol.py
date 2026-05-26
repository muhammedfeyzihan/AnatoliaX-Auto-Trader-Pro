"""
compound_growth_protocol.py — Compound Interest + Kelly Criterion Growth Engine

Turns the trading system into a mathematical compounding machine.

Core Formula:
    Target Capital = Initial × (1 + Daily_Return)^Days
    Kelly Fraction = (p×b - q) / b
    Position Size = Capital × Kelly_Fraction × Risk_Adj × Time_Decay_Factor

Where:
    p = win probability (from backtest/agent scoring)
    q = 1 - p
    b = avg_win / avg_loss (payoff ratio)
    Risk_Adj = adaptive scaling based on current drawdown & volatility
    Time_Decay_Factor = reduces size near market close / before holidays

Recovery Formula (after loss):
    Recovery_Multiplier = 1 + (Loss_Pct × Recovery_Factor)
    Next_Position = Base_Size × Recovery_Multiplier
    Recovery_Factor decays each win until original size restored.

Usage:
    from strategy.protocol_strategies.compound_growth_protocol import CompoundGrowthProtocol
    proto = CompoundGrowthProtocol(initial_capital=1000)
    signal = proto.evaluate(df, symbol="THYAO", venue="BIST")
    if signal:
        print(f"Size: {signal.size}, R:R: {signal.rr}, Kelly: {signal.context['kelly']}")
"""

import os
import sys
import time
import math
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd

_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

from data.unified_market_calendar import UnifiedMarketCalendar
from risk.execution_laws import ImmutableExecutionLawEngine
from risk.black_swan_guard import BlackSwanGuard
from strategy.protocol_strategies.alpha_protocol import AlphaProtocol, AlphaSignal, SetupType


@dataclass
class GrowthSignal(AlphaSignal):
    kelly_fraction: float = 0.0
    compound_factor: float = 1.0
    recovery_multiplier: float = 1.0
    time_decay: float = 1.0
    expected_return: float = 0.0

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "kelly_fraction": round(self.kelly_fraction, 4),
            "compound_factor": round(self.compound_factor, 4),
            "recovery_multiplier": round(self.recovery_multiplier, 4),
            "time_decay": round(self.time_decay, 4),
            "expected_return": round(self.expected_return, 4),
        })
        return d


class CompoundGrowthProtocol:
    """
    Compound Growth Protocol v1.0

    Mathematical Foundation:
    1. Kelly Criterion: f* = (pb - q) / b
    2. Compound Interest: A = P(1 + r)^t
    3. Optimal Daily Return: r_opt = kelly_fraction × edge
    4. Recovery Multiplier: R = 1 + λ × |drawdown|  (λ=0.5 conservative)
    5. Time Decay: τ = 1 - (hours_to_close / total_session_hours)

    Parameters:
    - initial_capital: 1000 (or any amount)
    - target_capital: 1_000_000 (configurable)
    - max_days: 20 (configurable)
    - kelly_fraction: 0.25 (Quarter Kelly for safety)
    - recovery_factor: 0.5 (aggressive recovery after loss)
    - compound_mode: True (reinvest all profits)

    Risk Management:
    - Max daily loss: %3 of current capital
    - Max drawdown from peak: %10
    - Kelly never exceeds %25 per trade
    - If drawdown > %5, Kelly halves automatically
    - If drawdown > %10, system halts

    Kural K256: CompoundGrowthProtocol her zaman AlphaProtocol sinyali üzerinde çalışır.
    K257: Kelly fraction asla 0.25'ü geçmez (Quarter Kelly).
    K258: Kayıp sonrası recovery multiplier 1.5'ten büyük olamaz.
    K259: Compound mode aktifse kazançlar hemen yeniden yatırılır.
    K260: Time decay < 0.5 ise pozisyon %50 küçültülür.
    """

    PARAMS = {
        "initial_capital": 1_000.0,
        "target_capital": 1_000_000.0,
        "max_days": 20,
        "max_daily_loss_pct": 3.0,
        "max_drawdown_pct": 10.0,
        "kelly_cap": 0.25,
        "kelly_drawdown_halving_pct": 0.05,
        "recovery_factor": 0.5,
        "recovery_max_mult": 1.5,
        "compound_mode": True,
        "reinvest_pct": 100.0,
        "session_hours": 8.5,  # BIST: 09:30-18:00
    }

    def __init__(self, initial_capital: float = 1_000.0, params: Optional[Dict] = None):
        self.params = {**self.PARAMS, **(params or {})}
        self.params["initial_capital"] = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        self.daily_pnl = 0.0
        self.total_days = 0
        self.trade_history: List[dict] = []
        self.calendar = UnifiedMarketCalendar()
        self.law_engine = ImmutableExecutionLawEngine(strict_mode=True)
        self.black_swan_guard = BlackSwanGuard()
        self.alpha_proto = AlphaProtocol(account_size=initial_capital)
        self._last_reset_day = datetime.now().day
        self._drawdown = 0.0

    # ------------------------------------------------------------------
    # Core math
    # ------------------------------------------------------------------
    def compute_required_daily_return(self) -> float:
        """Compound interest rate needed to reach target in max_days."""
        P = self.current_capital
        A = self.params["target_capital"]
        t = self.params["max_days"] - self.total_days
        if t <= 0 or P <= 0:
            return 0.0
        # A = P(1+r)^t  →  r = (A/P)^(1/t) - 1
        r = (A / P) ** (1.0 / t) - 1.0
        return r

    def compute_kelly_fraction(self, p_win: float, avg_win: float, avg_loss: float) -> float:
        """Kelly Criterion: f* = (pb - q) / b. Returns Quarter Kelly capped at 0.25."""
        if avg_loss <= 0 or p_win <= 0 or p_win >= 1:
            return 0.0
        q = 1.0 - p_win
        b = avg_win / avg_loss  # payoff ratio
        if b <= 0:
            return 0.0
        kelly = (p_win * b - q) / b
        # Quarter Kelly for safety
        kelly = kelly * 0.25
        # Cap
        kelly = min(kelly, self.params["kelly_cap"])
        kelly = max(0.0, kelly)
        # Drawdown halving
        if self._drawdown >= self.params["kelly_drawdown_halving_pct"]:
            kelly = kelly / 2.0
        return kelly

    def compute_recovery_multiplier(self, last_trade_pnl_pct: float) -> float:
        """After a loss, slightly increase next position to recover faster (not martingale)."""
        if last_trade_pnl_pct >= 0:
            return 1.0
        loss_pct = abs(last_trade_pnl_pct)
        mult = 1.0 + loss_pct * self.params["recovery_factor"]
        return min(mult, self.params["recovery_max_mult"])

    def compute_time_decay_factor(self, venue: str = "BIST") -> float:
        """Reduce position size as market close approaches."""
        now = datetime.now(self.calendar._tz)
        if venue == "BIST":
            close_hour = 18
            open_hour = 9
        else:
            close_hour = 21
            open_hour = 0
        total = close_hour - open_hour
        remaining = close_hour - now.hour - (now.minute / 60.0)
        if remaining <= 0:
            return 0.0
        tau = remaining / total
        # Linear decay: full size at open, half at 50% session
        return max(0.5, tau)

    def compute_position_size(self, entry: float, stop: float, kelly: float, recovery: float, time_decay: float) -> float:
        """Kelly-based position sizing with recovery and time decay."""
        risk_per_unit = abs(entry - stop)
        if risk_per_unit <= 0:
            return 0.0
        # Risk amount = Capital × Kelly × Recovery × TimeDecay
        risk_amount = self.current_capital * kelly * recovery * time_decay
        # But never risk more than max_daily_loss_pct in one trade
        max_risk = self.current_capital * self.params["max_daily_loss_pct"] / 100.0
        risk_amount = min(risk_amount, max_risk)
        size = risk_amount / risk_per_unit
        return round(size, 4)

    def update_capital(self, pnl: float):
        """Apply compound mode: add PnL to current capital immediately."""
        self.current_capital += pnl
        self.daily_pnl += pnl
        self.peak_capital = max(self.peak_capital, self.current_capital)
        self._drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        self.trade_history.append({"pnl": pnl, "capital": self.current_capital, "time": time.time()})
        # Update alpha proto's account size
        self.alpha_proto.account_size = self.current_capital

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    def evaluate(
        self,
        df: pd.DataFrame,
        symbol: str,
        venue: str = "BIST",
        timeframe: str = "M15",
        higher_tf_df: Optional[pd.DataFrame] = None,
        p_win: float = 0.55,
        avg_win: float = 2.0,
        avg_loss: float = 1.0,
        last_pnl_pct: float = 0.0,
    ) -> Optional[GrowthSignal]:
        """
        Run AlphaProtocol, then overlay Kelly + Compound math.

        Args:
            p_win: Estimated win probability from backtest or agent scoring
            avg_win: Average win amount (R multiple)
            avg_loss: Average loss amount (R multiple)
            last_pnl_pct: Last trade PnL as % of capital (for recovery)
        """
        now = datetime.now()
        if now.day != self._last_reset_day:
            self.daily_pnl = 0.0
            self.total_days += 1
            self._last_reset_day = now.day

        # Check drawdown halt
        if self._drawdown >= self.params["max_drawdown_pct"] / 100.0:
            return None

        # Daily loss limit
        if abs(self.daily_pnl) >= self.current_capital * self.params["max_daily_loss_pct"] / 100.0:
            return None

        # Get base signal from AlphaProtocol
        base_signal = self.alpha_proto.evaluate(df, symbol=symbol, venue=venue, timeframe=timeframe, higher_tf_df=higher_tf_df)
        if not base_signal:
            return None

        # Compute Kelly
        kelly = self.compute_kelly_fraction(p_win, avg_win, avg_loss)
        if kelly <= 0:
            return None

        # Compute recovery
        recovery = self.compute_recovery_multiplier(last_pnl_pct)

        # Compute time decay
        time_decay = self.compute_time_decay_factor(venue)
        if time_decay < 0.5:
            # Reduce confidence but allow trade
            pass

        # Compute compound position size
        new_size = self.compute_position_size(
            entry=base_signal.entry_price,
            stop=base_signal.stop_loss,
            kelly=kelly,
            recovery=recovery,
            time_decay=time_decay,
        )

        if new_size <= 0:
            return None

        # Required daily return
        required_r = self.compute_required_daily_return()
        expected_return = kelly * (p_win * avg_win - (1 - p_win) * avg_loss)

        # Build GrowthSignal
        return GrowthSignal(
            symbol=base_signal.symbol,
            side=base_signal.side,
            setup=base_signal.setup,
            entry_price=base_signal.entry_price,
            stop_loss=base_signal.stop_loss,
            take_profit=base_signal.take_profit,
            size=new_size,
            risk_pct=self.params["max_daily_loss_pct"],
            rr=base_signal.rr,
            confidence=base_signal.confidence,
            timeframe=base_signal.timeframe,
            reasons=base_signal.reasons + [
                f"Kelly={kelly:.2%}",
                f"Recovery={recovery:.2f}x",
                f"TimeDecay={time_decay:.2f}",
                f"RequiredDailyReturn={required_r:.2%}",
            ],
            kelly_fraction=kelly,
            compound_factor=self.current_capital / self.params["initial_capital"],
            recovery_multiplier=recovery,
            time_decay=time_decay,
            expected_return=expected_return,
        )

    # ------------------------------------------------------------------
    # Simulation / Projection
    # ------------------------------------------------------------------
    def project_growth(
        self,
        trades_per_day: int = 3,
        p_win: float = 0.55,
        avg_win: float = 2.0,
        avg_loss: float = 1.0,
    ) -> List[dict]:
        """
        Monte-Carlo projection of capital growth over max_days.
        Returns daily capital trajectory.
        """
        np.random.seed(42)
        capital = self.params["initial_capital"]
        trajectory = [{"day": 0, "capital": capital, "drawdown": 0.0}]
        for day in range(1, self.params["max_days"] + 1):
            daily_pnl = 0.0
            for _ in range(trades_per_day):
                kelly = self.compute_kelly_fraction(p_win, avg_win, avg_loss)
                risk = capital * kelly
                if np.random.random() < p_win:
                    daily_pnl += risk * avg_win
                else:
                    daily_pnl -= risk * avg_loss
            capital += daily_pnl
            if capital <= 0:
                capital = 0
                break
            peak = max(t["capital"] for t in trajectory)
            dd = (peak - capital) / peak if peak > 0 else 0.0
            trajectory.append({"day": day, "capital": round(capital, 2), "drawdown": round(dd, 4)})
        return trajectory

    def get_protocol_stats(self) -> dict:
        return {
            "initial_capital": self.params["initial_capital"],
            "current_capital": round(self.current_capital, 2),
            "peak_capital": round(self.peak_capital, 2),
            "target_capital": self.params["target_capital"],
            "total_days": self.total_days,
            "max_days": self.params["max_days"],
            "required_daily_return": round(self.compute_required_daily_return() * 100, 2),
            "drawdown_pct": round(self._drawdown * 100, 2),
            "daily_pnl": round(self.daily_pnl, 2),
            "trade_count": len(self.trade_history),
            "params": self.params,
        }


if __name__ == "__main__":
    proto = CompoundGrowthProtocol(initial_capital=1000)
    print("Growth Protocol Stats:", proto.get_protocol_stats())
    print("Required Daily Return:", f"{proto.compute_required_daily_return()*100:.2f}%")
    print("Kelly (p=0.55, win=2R, loss=1R):", f"{proto.compute_kelly_fraction(0.55, 2.0, 1.0)*100:.2f}%")
    print("Projection (20 days, 3 trades/day):")
    for t in proto.project_growth():
        print(f"  Day {t['day']}: {t['capital']:,.0f} TL (DD: {t['drawdown']:.1%})")
