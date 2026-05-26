"""
gold_mining/orchestrator.py — Progressive Tier Orchestrator

The heart of the Gold Mining strategy. Manages tier progression
(MS → S1 → M1 → M15), agent activation (1 → 1 → 2 → 3),
risk integration, and user-customizable rules.

Usage:
    from strategy.gold_mining.orchestrator import GoldMiningOrchestrator
    engine = GoldMiningOrchestrator(initial_capital=50_000)
    result = engine.process_symbol("THYAO", df_1m)
    engine.report_trade_result("THYAO", exit_price=105.0)
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any

import numpy as np
import pandas as pd

from strategy.gold_mining.tier_config import (
    TierConfig,
    TIER_DEFINITIONS,
    get_tier_by_name,
    get_next_tier,
    get_default_tier,
)
from strategy.gold_mining.ms_strategy import MSStrategy
from strategy.gold_mining.s1_strategy import S1Strategy
from strategy.gold_mining.m1_strategy import M1Strategy
from strategy.gold_mining.m5_strategy import M5Strategy
from strategy.gold_mining.m15_strategy import M15Strategy
from strategy.gold_mining.m30_strategy import M30Strategy
from strategy.gold_mining.h1_strategy import H1Strategy
from strategy.gold_mining.h2_strategy import H2Strategy
from strategy.gold_mining.d1_strategy import D1Strategy
from risk.position import Position
from risk.account import Account
from risk.kill_switch import KillSwitch


class GoldMiningState:
    """Persistent-like state for tier progression tracking."""

    def __init__(
        self,
        current_tier_name: str = "MS",
        consecutive_wins: int = 0,
        consecutive_losses: int = 0,
        total_trades: int = 0,
        winning_trades: int = 0,
        peak_equity: float = 0.0,
    ):
        self.current_tier_name = current_tier_name
        self.consecutive_wins = consecutive_wins
        self.consecutive_losses = consecutive_losses
        self.total_trades = total_trades
        self.winning_trades = winning_trades
        self.peak_equity = peak_equity

    @property
    def win_rate(self) -> float:
        if self.total_trades <= 0:
            return 0.0
        return self.winning_trades / self.total_trades

    def to_dict(self) -> dict:
        return {
            "current_tier_name": self.current_tier_name,
            "consecutive_wins": self.consecutive_wins,
            "consecutive_losses": self.consecutive_losses,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "win_rate": round(self.win_rate, 3),
            "peak_equity": self.peak_equity,
        }


class GoldMiningOrchestrator:
    """
    Progressive tier scalping orchestrator.

    Starts at MS (1 agent, 500ms bars) and graduates through
    S1 → M1 → M15 as capital and win streaks accumulate.
    Falls back to lower tiers on drawdown or consecutive losses.

    Customizable rules:
        - graduation_multiplier: capital multiplier required for next tier
        - fallback_drawdown_pct: equity drawdown triggering fallback
        - fallback_consecutive_losses: loss streak triggering fallback
        - max_agents_override: hard cap on agents (default 3)
        - kelly_fraction: fraction of Kelly to use (default 0.25)
        - max_risk_per_trade_pct: max equity risk per trade (default 2%)
    """

    def __init__(
        self,
        initial_capital: float = 100_000.0,
        rules: Optional[dict] = None,
        state: Optional[GoldMiningState] = None,
    ):
        self.rules = {
            "graduation_multiplier": 1.0,  # tier.min_capital * this
            "fallback_drawdown_pct": 0.05,  # 5% equity drawdown
            "fallback_consecutive_losses": 3,
            "max_agents_override": 3,
            "kelly_fraction": 0.25,
            "max_risk_per_trade_pct": 0.02,
            "require_manipulation_check": True,
            "require_kill_switch": True,
            "cooldown_seconds": 0.0,
        }
        if rules:
            self.rules.update(rules)

        self.account = Account(initial_cash=initial_capital)
        self.state = state or GoldMiningState(current_tier_name="MS")
        if self.state.peak_equity == 0.0:
            self.state.peak_equity = initial_capital

        self.kill_switch = KillSwitch(
            max_drawdown_pct=0.10,
            daily_loss_pct=0.05,
            consecutive_losses=5,
        )

        self._strategies: Dict[str, Any] = {
            "MS": MSStrategy(),
            "S1": S1Strategy(),
            "M1": M1Strategy(),
            "M5": M5Strategy(),
            "M15": M15Strategy(),
            "M30": M30Strategy(),
            "H1": H1Strategy(),
            "H2": H2Strategy(),
            "D1": D1Strategy(),
        }

        self._last_trade_time: Optional[datetime] = None

    # ------------------------------------------------------------------
    # Tier logic
    # ------------------------------------------------------------------
    @property
    def current_tier(self) -> TierConfig:
        tier = get_tier_by_name(self.state.current_tier_name)
        if tier is None:
            return get_default_tier()
        return tier

    def _can_graduate(self) -> bool:
        next_tier = get_next_tier(self.state.current_tier_name)
        if next_tier is None:
            return False

        realized = self.account.realized_pnl
        min_cap = next_tier.min_capital * self.rules["graduation_multiplier"]
        if realized < min_cap:
            return False

        if self.state.consecutive_wins < next_tier.required_consecutive_wins:
            return False

        if self.state.win_rate < next_tier.required_win_rate:
            return False

        return True

    def _should_fallback(self) -> bool:
        tier = self.current_tier
        if tier.name == "MS":
            return False

        if self.state.consecutive_losses >= self.rules["fallback_consecutive_losses"]:
            return True

        equity = self.account.equity
        if self.state.peak_equity > 0:
            dd = (self.state.peak_equity - equity) / self.state.peak_equity
            if dd >= self.rules["fallback_drawdown_pct"]:
                return True

        return False

    def _graduate(self) -> Optional[str]:
        next_tier = get_next_tier(self.state.current_tier_name)
        if next_tier is None:
            return None
        old = self.state.current_tier_name
        self.state.current_tier_name = next_tier.name
        self.state.consecutive_wins = 0
        self.state.consecutive_losses = 0
        return old

    def _fallback(self) -> Optional[str]:
        names = [t.name for t in TIER_DEFINITIONS]
        idx = names.index(self.state.current_tier_name)
        if idx <= 0:
            return None
        old = self.state.current_tier_name
        self.state.current_tier_name = names[idx - 1]
        self.state.consecutive_wins = 0
        self.state.consecutive_losses = 0
        return old

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_interval(tier_name: str) -> str:
        mapping = {
            "MS": "1m",
            "S1": "1m",
            "M1": "1m",
            "M5": "5m",
            "M15": "15m",
            "M30": "30m",
            "H1": "1h",
            "H2": "2h",
            "D1": "1d",
        }
        return mapping.get(tier_name, "1m")

    @staticmethod
    def _synthesize_micro_bar(last_row: pd.Series) -> dict:
        """Convert a 1m bar row into a synthetic micro-bar for MS strategy."""
        return {
            "timestamp": last_row.name if hasattr(last_row, "name") else datetime.now(),
            "open": float(last_row.get("open", last_row["close"])),
            "high": float(last_row.get("high", last_row["close"])),
            "low": float(last_row.get("low", last_row["close"])),
            "close": float(last_row["close"]),
            "bid_volume": float(last_row.get("volume", 0)) * 0.5,
            "ask_volume": float(last_row.get("volume", 0)) * 0.5,
            "total_volume": float(last_row.get("volume", 0)),
            "spread": float(last_row.get("spread", 0.0)),
        }

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------
    def generate_signal(
        self,
        symbol: str,
        df: pd.DataFrame,
        macro: Optional[dict] = None,
        sentiment: float = 0.0,
    ) -> Optional[dict]:
        """
        Generate a signal for *symbol* using the current tier's strategy.

        Parameters
        ----------
        df : pd.DataFrame
            Price bars appropriate for the tier (1m for MS/S1/M1, 15m for M15).
        macro : dict, optional
            For M15 tier: {"regime": "BULL|BEAR|NEUTRAL", "score": int}
        sentiment : float
            For M15 tier: -1 to +1

        Returns
        -------
        dict or None
            Signal dict enriched with tier and agent info, or None.
        """
        if df is None or df.empty:
            return None

        tier = self.current_tier
        strategy = self._strategies[tier.name]
        signal: Optional[dict] = None

        if tier.name == "MS":
            micro = self._synthesize_micro_bar(df.iloc[-1])
            signal = strategy.generate(micro)
        elif tier.name == "S1":
            signal = strategy.generate(df)
        elif tier.name == "M1":
            signal = strategy.generate(df)
            if signal and tier.max_agents >= 2:
                confirmed = strategy.confirm_secondary(df, signal)
                if not confirmed:
                    signal = None
        elif tier.name == "M5":
            signal = strategy.generate(df)
            if signal and tier.max_agents >= 2:
                confirmed = strategy.confirm_secondary(df, signal)
                if not confirmed:
                    signal = None
        elif tier.name in ("M15", "M30", "H1", "H2", "D1"):
            signal = strategy.generate(df, macro=macro or {"regime": "NEUTRAL", "score": 1}, sentiment=sentiment)
        else:
            return None

        if signal is None:
            return None

        # Enrich with orchestrator metadata
        signal["tier"] = tier.name
        signal["agents_active"] = min(tier.max_agents, self.rules["max_agents_override"])
        signal["symbol"] = symbol
        return signal

    # ------------------------------------------------------------------
    # Position sizing
    # ------------------------------------------------------------------
    def calculate_position_size(self, price: float, signal: dict) -> int:
        """
        Kelly-based position sizing capped at max_risk_per_trade_pct.
        Returns integer share quantity (BIST lot size = 1).
        """
        if price <= 0:
            return 0

        equity = self.account.equity
        if equity <= 0:
            return 0

        # Conservative Kelly fraction
        kelly_frac = self.rules["kelly_fraction"]
        max_risk = self.rules["max_risk_per_trade_pct"]

        # Fixed fractional: risk a percentage of equity
        risk_pct = min(kelly_frac * 0.1, max_risk)  # 0.1 is a proxy for edge
        notional = equity * risk_pct
        qty = int(notional / price)
        return max(qty, 1)

    # ------------------------------------------------------------------
    # Execution simulation
    # ------------------------------------------------------------------
    def process_symbol(
        self,
        symbol: str,
        df: pd.DataFrame,
        macro: Optional[dict] = None,
        sentiment: float = 0.0,
        current_price: Optional[float] = None,
    ) -> dict:
        """
        Full pipeline: signal → risk → execution → result.

        Returns
        -------
        dict
            {
                "symbol", "signal", "executed", "tier", "agents_active",
                "quantity", "reason", "commission", "account_state"
            }
        """
        result = {
            "symbol": symbol,
            "signal": None,
            "executed": False,
            "tier": self.state.current_tier_name,
            "agents_active": 0,
            "quantity": 0,
            "reason": "",
            "commission": 0.0,
            "account_state": self.account.to_dict(),
        }

        # Kill switch
        if self.rules["require_kill_switch"] and not self.kill_switch.is_alive():
            result["reason"] = "KILL_SWITCH_ACTIVE"
            return result

        # Cooldown
        if self._last_trade_time is not None and self.rules["cooldown_seconds"] > 0:
            elapsed = (datetime.now() - self._last_trade_time).total_seconds()
            if elapsed < self.rules["cooldown_seconds"]:
                result["reason"] = f"COOLDOWN: {elapsed:.0f}s remaining"
                return result

        # Signal
        signal = self.generate_signal(symbol, df, macro=macro, sentiment=sentiment)
        if signal is None:
            result["reason"] = "NO_SIGNAL"
            return result

        result["signal"] = signal
        result["tier"] = signal.get("tier", self.state.current_tier_name)
        result["agents_active"] = signal.get("agents_active", 1)

        price = signal["entry"]
        qty = self.calculate_position_size(price, signal)
        if qty <= 0:
            result["reason"] = "POSITION_SIZE_ZERO"
            return result

        # Pre-trade risk via Account
        allowed, reason = self.account.can_open_position(symbol, qty, price)
        if not allowed:
            result["reason"] = f"RISK_GATE: {reason}"
            return result

        # Commission ~0.4% round-trip; charge half on entry
        commission = price * qty * 0.002
        success = self.account.open_position(symbol, qty, price, commission)

        if success:
            self._last_trade_time = datetime.now()
            result["executed"] = True
            result["quantity"] = qty
            result["commission"] = commission
            result["reason"] = "EXECUTED"
        else:
            result["reason"] = "ACCOUNT_OPEN_FAILED"

        result["account_state"] = self.account.to_dict()
        return result

    # ------------------------------------------------------------------
    # Trade result reporting (drives tier progression)
    # ------------------------------------------------------------------
    def report_trade_result(
        self,
        symbol: str,
        exit_price: float,
        exit_commission: Optional[float] = None,
    ) -> dict:
        """
        Close a position, update P&L, streaks, and evaluate tier changes.

        Returns
        -------
        dict with pnl, tier_change, and state snapshot.
        """
        result = {
            "symbol": symbol,
            "pnl": 0.0,
            "realized": 0.0,
            "tier_change": None,
            "state": self.state.to_dict(),
        }

        pos = self.account.get_position(symbol)
        if pos is None or not pos.is_open:
            result["reason"] = "NO_OPEN_POSITION"
            return result

        qty = pos.quantity
        if exit_commission is None:
            exit_commission = exit_price * qty * 0.002

        pnl = self.account.close_position(symbol, qty, exit_price, exit_commission)
        realized = pnl if pnl is not None else 0.0
        result["pnl"] = realized
        result["realized"] = realized

        # Update state
        self.state.total_trades += 1
        if realized > 0:
            self.state.winning_trades += 1
            self.state.consecutive_wins += 1
            self.state.consecutive_losses = 0
        else:
            self.state.consecutive_wins = 0
            self.state.consecutive_losses += 1

        # Peak equity tracking
        equity = self.account.equity
        if equity > self.state.peak_equity:
            self.state.peak_equity = equity

        # Kill switch
        self.kill_switch.update(equity, self.account.realized_pnl, realized)

        # Tier evaluation
        if self._can_graduate():
            old = self._graduate()
            result["tier_change"] = f"GRADUATE: {old} → {self.state.current_tier_name}"
        elif self._should_fallback():
            old = self._fallback()
            result["tier_change"] = f"FALLBACK: {old} → {self.state.current_tier_name}"

        result["state"] = self.state.to_dict()
        result["account"] = self.account.to_dict()
        return result

    # ------------------------------------------------------------------
    # Batch / scan helpers
    # ------------------------------------------------------------------
    def run_scan(
        self,
        symbols: list[str],
        data_provider,
        macro: Optional[dict] = None,
        sentiment: float = 0.0,
    ) -> list[dict]:
        """
        Scan a list of symbols and return execution results.
        `data_provider` is a callable: provider(symbol, interval) -> pd.DataFrame
        """
        interval = self._resolve_interval(self.state.current_tier_name)
        results = []
        for sym in symbols:
            try:
                df = data_provider(sym, interval)
                res = self.process_symbol(sym, df, macro=macro, sentiment=sentiment)
                results.append(res)
            except Exception as e:
                results.append({"symbol": sym, "executed": False, "reason": f"ERROR: {e}"})
        return results

    # ------------------------------------------------------------------
    # Manual exit
    # ------------------------------------------------------------------
    def manual_exit(
        self,
        symbol: str,
        exit_price: float,
        reason: str = "MANUAL",
    ) -> dict:
        """
        Kullanıcı tarafından manuel pozisyon kapatma.
        Bypasses normal SL/TP, closes immediately.

        Returns
        -------
        dict with pnl, exit reason, and state.
        """
        result = {
            "symbol": symbol,
            "pnl": 0.0,
            "realized": 0.0,
            "tier_change": None,
            "exit_type": "MANUAL",
            "exit_reason": reason,
            "state": self.state.to_dict(),
        }

        pos = self.account.get_position(symbol)
        if pos is None or not pos.is_open:
            result["reason"] = "NO_OPEN_POSITION"
            return result

        qty = pos.quantity
        exit_commission = exit_price * qty * 0.002
        pnl = self.account.close_position(symbol, qty, exit_price, exit_commission)
        realized = pnl if pnl is not None else 0.0
        result["pnl"] = realized
        result["realized"] = realized

        # Update state
        self.state.total_trades += 1
        if realized > 0:
            self.state.winning_trades += 1
            self.state.consecutive_wins += 1
            self.state.consecutive_losses = 0
        else:
            self.state.consecutive_wins = 0
            self.state.consecutive_losses += 1

        equity = self.account.equity
        if equity > self.state.peak_equity:
            self.state.peak_equity = equity

        self.kill_switch.update(equity, self.account.realized_pnl, realized)

        if self._can_graduate():
            old = self._graduate()
            result["tier_change"] = f"GRADUATE: {old} → {self.state.current_tier_name}"
        elif self._should_fallback():
            old = self._fallback()
            result["tier_change"] = f"FALLBACK: {old} → {self.state.current_tier_name}"

        result["state"] = self.state.to_dict()
        result["account"] = self.account.to_dict()
        return result

    # ------------------------------------------------------------------
    # Adaptive tier selection
    # ------------------------------------------------------------------
    def auto_select_tier(
        self,
        df: pd.DataFrame,
        macro: Optional[dict] = None,
    ) -> str:
        """
        Piyasa kosullarina gore en iyi tier'i otomatik sec.
        Degisiklik olursa state'i gunceller.

        Returns
        -------
        str: recommended tier name
        """
        from strategy.gold_mining.adaptive_selector import AdaptiveTierSelector
        selector = AdaptiveTierSelector()
        recommended = selector.select(df, macro=macro)

        # Only auto-switch if current tier is not locked by user
        if self.rules.get("auto_tier_switch", True):
            if recommended != self.state.current_tier_name:
                old = self.state.current_tier_name
                self.state.current_tier_name = recommended
                # Reset streaks on tier change
                self.state.consecutive_wins = 0
                self.state.consecutive_losses = 0
                return recommended
        return self.state.current_tier_name

    # ------------------------------------------------------------------
    # State persistence helpers
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "rules": self.rules,
            "state": self.state.to_dict(),
            "account": self.account.to_dict(),
            "kill_switch_alive": self.kill_switch.is_alive(),
            "current_tier_name": self.current_tier.name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GoldMiningOrchestrator":
        state_data = data.get("state", {}).copy()
        state_data.pop("win_rate", None)  # derived property
        state = GoldMiningState(**state_data)
        inst = cls(
            initial_capital=data.get("account", {}).get("initial_cash", 100_000.0),
            rules=data.get("rules"),
            state=state,
        )
        # Restore account cash / PnL
        inst.account.cash = data.get("account", {}).get("cash", inst.account.initial_cash)
        inst.account.realized_pnl = data.get("account", {}).get("realized_pnl", 0.0)
        return inst
