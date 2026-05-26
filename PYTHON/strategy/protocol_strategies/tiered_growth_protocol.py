"""
tiered_growth_protocol.py — Tiered Daily Return Strategy System

Mevcut stratejileri (AlphaProtocol, CompoundGrowthProtocol, OmegaProtocol,
GoldMiningOrchestrator) bozmadan, günlük getiri hedeflerine göre optimize
edilmiş risk-parametre katmanları sunar.

Hedef Günlük Getiriler:
  %1   — Conservative (emeklilik fonu tarzı, düşük risk)
  %3   — Moderate (ortama risk, günlük swing)
  %5   — Aggressive (yüksek aktivite, momentum)
  %8   — Very Aggressive (kısa vadeli, yüksek konviksiyon)
  %10  — Extreme (günlük hedef %10, sık işlem)
  %13  — Ultra (büyük pozisyon, az işlem)
  %15  — Hyper (tek işlemle günü kapatma hedefi)
  %18  — Mega (yarım günde %18, yoğun scalp)
  %20  — Apex (teorik maksimum, tek işlem)
  %100 — Theoretical (MATEMATİKSEL OLARAK MÜMKÜN AMA PRAKTE NEREDEYSE İMKANSIZ,
                     aşırı kaldıraç, tek nokta başarısızlığı = sıfırlanma)

Matematiksel Temel:
  Aylık Bileşik = (1 + daily)^22 - 1
  Yıllık Bileşik = (1 + daily)^252 - 1
  Kelly Fraction = (p*b - q) / b
  Pozisyon Boyutu = Sermaye × Kelly × Risk Ayarı × Zaman Çürümesi

Risk-Uygunluk Matrisi:
  %1   : Kelly 0.05, R:R 1.5, p_win 0.60, max_dd 3%,  günlük 3-5 işlem
  %3   : Kelly 0.10, R:R 2.0, p_win 0.55, max_dd 5%,  günlük 3-5 işlem
  %5   : Kelly 0.15, R:R 2.5, p_win 0.52, max_dd 8%,  günlük 2-4 işlem
  %8   : Kelly 0.18, R:R 3.0, p_win 0.50, max_dd 12%, günlük 2-3 işlem
  %10  : Kelly 0.20, R:R 3.5, p_win 0.48, max_dd 15%, günlük 1-3 işlem
  %13  : Kelly 0.22, R:R 4.0, p_win 0.45, max_dd 20%, günlük 1-2 işlem
  %15  : Kelly 0.23, R:R 4.5, p_win 0.43, max_dd 25%, günlük 1-2 işlem
  %18  : Kelly 0.24, R:R 5.0, p_win 0.40, max_dd 30%, günlük 1 işlem
  %20  : Kelly 0.25, R:R 5.5, p_win 0.38, max_dd 35%, günlük 1 işlem
  %100 : Kelly 0.25, R:R 10+, p_win 0.30, max_dd 80%, günlük 0-1 işlem (TEORİK)

Kural K272: %100 günlük hedef sadece simülasyon/test içindir; canlıda AKTİF DEĞİLDİR.
Kural K273: Her tier ayrı ayrı kullanılabilir; birbirine bağımlı değildir.
Kural K274: Tier seçimi sermaye büyüklüğüne ve risk toleransına göre yapılır.

Usage:
    from strategy.protocol_strategies.tiered_growth_protocol import TieredGrowthProtocol, DailyReturnTarget
    proto = TieredGrowthProtocol(initial_capital=10_000, target=DailyReturnTarget.PCT_5)
    signal = proto.evaluate(df, symbol="THYAO")
"""

import os
import sys
import math
import time
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum

import numpy as np
import pandas as pd

_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

from strategy.protocol_strategies.alpha_protocol import AlphaProtocol, AlphaSignal, SetupType
from strategy.protocol_strategies.compound_growth_protocol import CompoundGrowthProtocol, GrowthSignal
from strategy.protocol_strategies.omega_protocol import OmegaProtocol, PipelineConfig
from strategy.gold_mining.orchestrator import GoldMiningOrchestrator, GoldMiningState
from data.unified_market_calendar import UnifiedMarketCalendar
from risk.black_swan_guard import BlackSwanGuard


class DailyReturnTarget(Enum):
    PCT_1 = 0.01   # Conservative
    PCT_3 = 0.03   # Moderate
    PCT_5 = 0.05   # Aggressive
    PCT_8 = 0.08   # Very Aggressive
    PCT_10 = 0.10  # Extreme
    PCT_13 = 0.13  # Ultra
    PCT_15 = 0.15  # Hyper
    PCT_18 = 0.18  # Mega
    PCT_20 = 0.20  # Apex
    PCT_100 = 1.00 # Theoretical / Simulation only


@dataclass
class TieredRiskConfig:
    """Risk parameters calibrated for a specific daily return target."""
    target_name: str
    daily_return_pct: float
    kelly_cap: float
    min_rr: float
    target_win_rate: float
    max_drawdown_pct: float
    trades_per_day: Tuple[int, int]
    position_size_cap_pct: float   # Max capital per trade
    leverage: float                # 1.0 = no leverage
    timeframes: List[str]
    holding_hours: Tuple[float, float]
    slippage_tolerance_pct: float
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "target": self.target_name,
            "daily_return_pct": round(self.daily_return_pct * 100, 2),
            "kelly_cap": self.kelly_cap,
            "min_rr": self.min_rr,
            "target_win_rate": self.target_win_rate,
            "max_drawdown_pct": self.max_drawdown_pct,
            "trades_per_day": self.trades_per_day,
            "position_size_cap_pct": self.position_size_cap_pct,
            "leverage": self.leverage,
            "timeframes": self.timeframes,
            "holding_hours": self.holding_hours,
            "slippage_tolerance_pct": self.slippage_tolerance_pct,
            "description": self.description,
        }


# ------------------------------------------------------------------
# Pre-computed tier configurations (mathematically calibrated)
# ------------------------------------------------------------------
TIER_CONFIGS: Dict[DailyReturnTarget, TieredRiskConfig] = {
    DailyReturnTarget.PCT_1: TieredRiskConfig(
        target_name="Conservative",
        daily_return_pct=0.01,
        kelly_cap=0.05,
        min_rr=1.5,
        target_win_rate=0.60,
        max_drawdown_pct=3.0,
        trades_per_day=(3, 5),
        position_size_cap_pct=2.0,
        leverage=1.0,
        timeframes=["M15", "H1"],
        holding_hours=(0.5, 4.0),
        slippage_tolerance_pct=0.005,
        description="Emeklilik fonu tarzı. Düşük risk, yüksek kazanma oranı, sık küçük kazançlar.",
    ),
    DailyReturnTarget.PCT_3: TieredRiskConfig(
        target_name="Moderate",
        daily_return_pct=0.03,
        kelly_cap=0.10,
        min_rr=2.0,
        target_win_rate=0.55,
        max_drawdown_pct=5.0,
        trades_per_day=(3, 5),
        position_size_cap_pct=3.5,
        leverage=1.0,
        timeframes=["M15", "H1", "M5"],
        holding_hours=(0.5, 6.0),
        slippage_tolerance_pct=0.007,
        description="Günlük swing. Orta risk, momentum takibi, kademeli TP.",
    ),
    DailyReturnTarget.PCT_5: TieredRiskConfig(
        target_name="Aggressive",
        daily_return_pct=0.05,
        kelly_cap=0.15,
        min_rr=2.5,
        target_win_rate=0.52,
        max_drawdown_pct=8.0,
        trades_per_day=(2, 4),
        position_size_cap_pct=5.0,
        leverage=1.0,
        timeframes=["M5", "M15", "H1"],
        holding_hours=(0.25, 4.0),
        slippage_tolerance_pct=0.010,
        description="Yüksek aktivite. BB squeeze + volume breakout, 2-4 işlem/gün.",
    ),
    DailyReturnTarget.PCT_8: TieredRiskConfig(
        target_name="Very Aggressive",
        daily_return_pct=0.08,
        kelly_cap=0.18,
        min_rr=3.0,
        target_win_rate=0.50,
        max_drawdown_pct=12.0,
        trades_per_day=(2, 3),
        position_size_cap_pct=7.0,
        leverage=1.0,
        timeframes=["M5", "M15"],
        holding_hours=(0.25, 3.0),
        slippage_tolerance_pct=0.015,
        description="Kısa vadeli yüksek konviksiyon. Tek setup'a büyük pozisyon.",
    ),
    DailyReturnTarget.PCT_10: TieredRiskConfig(
        target_name="Extreme",
        daily_return_pct=0.10,
        kelly_cap=0.20,
        min_rr=3.5,
        target_win_rate=0.48,
        max_drawdown_pct=15.0,
        trades_per_day=(1, 3),
        position_size_cap_pct=10.0,
        leverage=1.0,
        timeframes=["M5", "M15"],
        holding_hours=(0.25, 2.0),
        slippage_tolerance_pct=0.020,
        description="Günlük hedef %10. Sadece A+ setup'lar, hızlı scalp.",
    ),
    DailyReturnTarget.PCT_13: TieredRiskConfig(
        target_name="Ultra",
        daily_return_pct=0.13,
        kelly_cap=0.22,
        min_rr=4.0,
        target_win_rate=0.45,
        max_drawdown_pct=20.0,
        trades_per_day=(1, 2),
        position_size_cap_pct=15.0,
        leverage=1.0,
        timeframes=["M5", "M1"],
        holding_hours=(0.1, 1.5),
        slippage_tolerance_pct=0.025,
        description="Büyük pozisyon, az işlem. 1-2 işlemle günü kapatma.",
    ),
    DailyReturnTarget.PCT_15: TieredRiskConfig(
        target_name="Hyper",
        daily_return_pct=0.15,
        kelly_cap=0.23,
        min_rr=4.5,
        target_win_rate=0.43,
        max_drawdown_pct=25.0,
        trades_per_day=(1, 2),
        position_size_cap_pct=20.0,
        leverage=1.0,
        timeframes=["M1", "M5"],
        holding_hours=(0.1, 1.0),
        slippage_tolerance_pct=0.030,
        description="Tek işlemle %15 hedef. Yarım saatlik momentum patlaması.",
    ),
    DailyReturnTarget.PCT_18: TieredRiskConfig(
        target_name="Mega",
        daily_return_pct=0.18,
        kelly_cap=0.24,
        min_rr=5.0,
        target_win_rate=0.40,
        max_drawdown_pct=30.0,
        trades_per_day=(1, 1),
        position_size_cap_pct=25.0,
        leverage=1.0,
        timeframes=["M1", "S1"],
        holding_hours=(0.05, 0.75),
        slippage_tolerance_pct=0.040,
        description="Yarım günde %18. Tek scalp, maksimum konviksiyon.",
    ),
    DailyReturnTarget.PCT_20: TieredRiskConfig(
        target_name="Apex",
        daily_return_pct=0.20,
        kelly_cap=0.25,
        min_rr=5.5,
        target_win_rate=0.38,
        max_drawdown_pct=35.0,
        trades_per_day=(1, 1),
        position_size_cap_pct=25.0,
        leverage=1.0,
        timeframes=["M1", "S1"],
        holding_hours=(0.05, 0.5),
        slippage_tolerance_pct=0.050,
        description="Teorik maksimum. Tek işlem, ATR*3 TP, yarım saat.",
    ),
    DailyReturnTarget.PCT_100: TieredRiskConfig(
        target_name="Theoretical",
        daily_return_pct=1.00,
        kelly_cap=0.25,
        min_rr=10.0,
        target_win_rate=0.30,
        max_drawdown_pct=80.0,
        trades_per_day=(0, 1),
        position_size_cap_pct=25.0,
        leverage=1.0,
        timeframes=["S1", "MS"],
        holding_hours=(0.01, 0.25),
        slippage_tolerance_pct=0.100,
        description="MATEMATİKSEL OLARAK MÜMKÜN AMA PRAKTE NEREDEYSE İMKANSIZ. Simülasyon/test içindir.",
    ),
}


@dataclass
class MonthlyProjection:
    target: DailyReturnTarget
    initial_capital: float
    trading_days: int = 22
    final_capital: float = 0.0
    total_return_pct: float = 0.0
    max_expected_dd_pct: float = 0.0
    avg_trades_per_day: int = 0
    total_trades: int = 0
    win_rate_needed: float = 0.0
    recommended_kelly: float = 0.0
    recommended_leverage: float = 1.0
    risk_of_ruin: float = 0.0

    def to_dict(self) -> dict:
        return {
            "tier": self.target.name,
            "initial_capital": round(self.initial_capital, 2),
            "trading_days": self.trading_days,
            "final_capital": round(self.final_capital, 2),
            "total_return_pct": round(self.total_return_pct, 2),
            "max_expected_dd_pct": round(self.max_expected_dd_pct, 2),
            "avg_trades_per_day": self.avg_trades_per_day,
            "total_trades": self.total_trades,
            "win_rate_needed": round(self.win_rate_needed, 2),
            "recommended_kelly": round(self.recommended_kelly, 4),
            "recommended_leverage": self.recommended_leverage,
            "risk_of_ruin": round(self.risk_of_ruin, 4),
        }


class TieredGrowthProtocol:
    """
    Tiered Growth Protocol v1.0

    Her günlük getiri hedefi için optimize edilmiş risk-parametre katmanı.
    Mevcut stratejileri (Alpha, Compound, Omega, GoldMining) çağırır,
    hedefe göre parametreleri override eder.
    """

    def __init__(
        self,
        initial_capital: float = 10_000.0,
        target: DailyReturnTarget = DailyReturnTarget.PCT_5,
        params: Optional[Dict] = None,
    ):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.target = target
        self.config = TIER_CONFIGS[target]
        self.params = params or {}

        # Subsystems (initialized lazily or on demand)
        self.alpha_proto: Optional[AlphaProtocol] = None
        self.compound_proto: Optional[CompoundGrowthProtocol] = None
        self.omega_proto: Optional[OmegaProtocol] = None
        self.gold_orchestrator: Optional[GoldMiningOrchestrator] = None
        self.calendar = UnifiedMarketCalendar()
        self.black_swan = BlackSwanGuard()

        self.trade_history: List[dict] = []
        self._last_reset_day = datetime.now().day

    # ------------------------------------------------------------------
    # Mathematical projections
    # ------------------------------------------------------------------
    @staticmethod
    def compound_return(daily_return_pct: float, days: int) -> float:
        """Total compound return over N days."""
        return (1.0 + daily_return_pct) ** days - 1.0

    @staticmethod
    def required_win_rate(rr: float, kelly: float) -> float:
        """Solve Kelly for win rate: f = (p*b - q)/b  ->  p = (f*b + 1)/(b+1)."""
        b = rr
        p = (kelly * b + 1.0) / (b + 1.0)
        return max(0.0, min(1.0, p))

    @staticmethod
    def risk_of_ruin(win_rate: float, avg_win: float, avg_loss: float, kelly: float, trades: int) -> float:
        """Approximate risk of ruin using Gambler's Ruin formula."""
        if avg_loss <= 0 or win_rate >= 1.0:
            return 0.0
        q = 1.0 - win_rate
        edge = win_rate * avg_win - q * avg_loss
        if edge <= 0:
            return 1.0
        # Simplified: R ≈ exp(-2 * edge * capital / variance)
        variance = win_rate * (avg_win ** 2) + q * (avg_loss ** 2) - (win_rate * avg_win - q * avg_loss) ** 2
        if variance <= 0:
            return 0.0
        # ruin factor with number of trades
        r = math.exp(-2.0 * edge * kelly / max(variance, 1e-9))
        return min(1.0, r ** trades)

    def get_monthly_projection(self, trading_days: int = 22) -> MonthlyProjection:
        """Return a forward-looking projection for the current tier."""
        cfg = self.config
        total_return = self.compound_return(cfg.daily_return_pct, trading_days)
        final = self.initial_capital * (1.0 + total_return)
        avg_trades = (cfg.trades_per_day[0] + cfg.trades_per_day[1]) // 2
        total_trades = avg_trades * trading_days
        p_needed = self.required_win_rate(cfg.min_rr, cfg.kelly_cap)
        ruin = self.risk_of_ruin(
            p_needed, cfg.min_rr, 1.0, cfg.kelly_cap, total_trades
        )
        return MonthlyProjection(
            target=self.target,
            initial_capital=self.initial_capital,
            trading_days=trading_days,
            final_capital=final,
            total_return_pct=total_return * 100,
            max_expected_dd_pct=cfg.max_drawdown_pct,
            avg_trades_per_day=avg_trades,
            total_trades=total_trades,
            win_rate_needed=p_needed,
            recommended_kelly=cfg.kelly_cap,
            recommended_leverage=cfg.leverage,
            risk_of_ruin=ruin,
        )

    def get_all_tier_projections(self, capital: Optional[float] = None) -> Dict[str, MonthlyProjection]:
        """Return monthly projections for ALL tiers (for comparison)."""
        base = capital or self.initial_capital
        results = {}
        for tier in DailyReturnTarget:
            proto = TieredGrowthProtocol(initial_capital=base, target=tier)
            results[tier.name] = proto.get_monthly_projection()
        return results

    # ------------------------------------------------------------------
    # Strategy selection per tier
    # ------------------------------------------------------------------
    def _select_strategy_for_tier(
        self,
        df: pd.DataFrame,
        symbol: str,
        venue: str = "BIST",
        higher_tf_df: Optional[pd.DataFrame] = None,
    ) -> Optional[Any]:
        """Delegate to the most appropriate underlying strategy for this tier."""
        cfg = self.config
        daily = cfg.daily_return_pct

        # Conservative / Moderate -> AlphaProtocol with adjusted params
        if daily <= 0.03:
            if self.alpha_proto is None:
                self.alpha_proto = AlphaProtocol(
                    account_size=self.current_capital,
                    params={
                        "max_risk_per_trade_pct": cfg.position_size_cap_pct / 10.0,
                        "min_rr": cfg.min_rr,
                        "max_daily_drawdown_pct": cfg.max_drawdown_pct,
                    }
                )
            return self.alpha_proto.evaluate(df, symbol=symbol, venue=venue, higher_tf_df=higher_tf_df)

        # Aggressive / Very Aggressive -> CompoundGrowthProtocol
        if daily <= 0.08:
            if self.compound_proto is None:
                self.compound_proto = CompoundGrowthProtocol(initial_capital=self.current_capital)
            self.compound_proto.current_capital = self.current_capital
            self.compound_proto.params["kelly_cap"] = cfg.kelly_cap
            self.compound_proto.params["max_daily_loss_pct"] = cfg.max_drawdown_pct / 3.0
            return self.compound_proto.evaluate(
                df, symbol=symbol, venue=venue, higher_tf_df=higher_tf_df,
                p_win=cfg.target_win_rate, avg_win=cfg.min_rr, avg_loss=1.0,
            )

        # Extreme / Ultra / Hyper -> OmegaProtocol with light config
        if daily <= 0.15:
            if self.omega_proto is None:
                self.omega_proto = OmegaProtocol(initial_capital=self.current_capital)
            self.omega_proto.current_capital = self.current_capital
            light_cfg = PipelineConfig(
                enable_worldmonitor=True,
                enable_black_swan=True,
                enable_calendar=True,
                enable_manipulation=True,
                enable_alpha_protocol=True,
                enable_compound_growth=True,
                enable_agent_council=True,
                enable_risk_gate=True,
                enable_immutable_laws=True,
                enable_skill_engine=False,
                enable_shared_memory=False,
                enable_portfolio=False,
                enable_ensemble=False,
                enable_openclaw=False,
                enable_symbol_rotation=False,
            )
            return self.omega_proto.evaluate(
                df, symbol=symbol, venue=venue, higher_tf_df=higher_tf_df,
                p_win=cfg.target_win_rate, avg_win=cfg.min_rr, avg_loss=1.0,
                config=light_cfg,
            )

        # Mega / Apex / Theoretical -> GoldMiningOrchestrator (fastest tiers)
        if self.gold_orchestrator is None:
            state = GoldMiningState(current_tier_name="M1" if daily <= 0.20 else "MS")
            self.gold_orchestrator = GoldMiningOrchestrator(
                initial_capital=self.current_capital,
                rules={"max_risk_per_trade_pct": cfg.position_size_cap_pct / 10.0},
                state=state,
            )
        return self.gold_orchestrator.process_symbol(symbol, df)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def evaluate(
        self,
        df: pd.DataFrame,
        symbol: str,
        venue: str = "BIST",
        higher_tf_df: Optional[pd.DataFrame] = None,
    ) -> Optional[Dict]:
        """
        Evaluate a single symbol through the tier-appropriate strategy.
        Returns a dict with signal details + tier metadata.
        """
        now = datetime.now()
        if now.day != self._last_reset_day:
            self._last_reset_day = now.day

        # Black swan / calendar checks
        if not self.calendar.is_market_open(venue):
            return None
        if self.black_swan.is_halted():
            return None

        raw_signal = self._select_strategy_for_tier(df, symbol, venue, higher_tf_df)
        if raw_signal is None:
            return None

        # Wrap with tier metadata
        result = {
            "tier": self.target.name,
            "tier_config": self.config.to_dict(),
            "capital": round(self.current_capital, 2),
            "monthly_projection": self.get_monthly_projection().to_dict(),
        }

        # Unify different signal types
        if hasattr(raw_signal, "to_dict"):
            result["signal"] = raw_signal.to_dict()
        elif isinstance(raw_signal, dict):
            result["signal"] = raw_signal
        else:
            result["signal"] = {"raw": str(raw_signal)}

        self.trade_history.append(result)
        return result

    def update_capital(self, pnl: float):
        """Apply PnL and update peak/drawdown."""
        self.current_capital += pnl
        if self.current_capital > self.initial_capital:
            self.initial_capital = self.current_capital  # peak tracking simplified

    def get_tier_comparison_table(self, capital: Optional[float] = None) -> pd.DataFrame:
        """Return a DataFrame comparing all tiers side-by-side."""
        projs = self.get_all_tier_projections(capital)
        rows = []
        for tier_name, proj in projs.items():
            rows.append({
                "Tier": tier_name,
                "Daily %": proj.target.value * 100,
                "Monthly %": round(proj.total_return_pct, 1),
                "Final Capital": round(proj.final_capital, 0),
                "Win Rate Needed": proj.win_rate_needed,
                "Kelly": proj.recommended_kelly,
                "Max DD": proj.max_expected_dd_pct,
                "Trades/Day": proj.avg_trades_per_day,
                "Risk of Ruin": proj.risk_of_ruin,
            })
        return pd.DataFrame(rows)

    def get_stats(self) -> dict:
        """Return current protocol stats."""
        proj = self.get_monthly_projection()
        return {
            "current_capital": round(self.current_capital, 2),
            "target_tier": self.target.name,
            "target_daily_return_pct": round(self.config.daily_return_pct * 100, 2),
            "monthly_projection": proj.to_dict(),
            "total_trades_evaluated": len(self.trade_history),
        }


if __name__ == "__main__":
    print("=== Tiered Growth Protocol — Tier Comparison Table ===\n")
    proto = TieredGrowthProtocol(initial_capital=10_000, target=DailyReturnTarget.PCT_5)
    df = proto.get_tier_comparison_table(capital=10_000)
    print(df.to_string(index=False))
    print("\n=== Monthly Projection (PCT_5) ===")
    proj = proto.get_monthly_projection()
    for k, v in proj.to_dict().items():
        print(f"  {k}: {v}")
