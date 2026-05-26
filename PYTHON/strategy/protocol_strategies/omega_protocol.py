"""
omega_protocol.py — Omega Protocol: The Final Unified Strategy

Combines EVERY subsystem of AnatoliaX into a single execution pipeline:
  - AlphaProtocol (10-gate TA)
  - CompoundGrowthProtocol (Kelly + compound math)
  - AgentCouncil (Ruflo consensus + manipulation veto)
  - WorldMonitorBridge (macro + news + halt detection)
  - ManipulationDetector (6-layer spoof/pump/wash detection)
  - BlackSwanGuard (5-layer crash detection)
  - Hermes RiskGateEngine (10 independent gates)
  - ImmutableExecutionLawEngine (15 pre-trade laws)
  - SkillEngine (self-improving trade skills)
  - SharedExperienceMemory (cross-agent lessons)
  - PortfolioOrchestrator (dynamic capital allocation)
  - DynamicSymbolRotator (best-symbol selection)
  - EnsembleOptimizer (regime-based strategy weights)
  - OpenClawRouter (agent routing)

Target: 1,000 TL -> 1,000,000 TL in max 20 trading days.
Mathematical basis:
  Required daily return r = (Target / Capital)^(1/days) - 1
  For 20 days: r ≈ 41.2% per day (aggressive but edge-driven).
  Quarter-Kelly caps risk per trade at 25% of capital max.
  Recovery multiplier accelerates after losses (not martingale).
  Time-decay shrinks size near market close.
  Kademeli TP + trailing ensures profit capture.

Kural K268: OmegaProtocol, tüm alt sistemlerin ONAY vermesi şartıyla çalışır.
Kural K269: 1000TL -> 1M TL hedefi matematiksel olarak mümkündür;
             fakat gerçek piyasada %41 günlük getiri çok nadirdir.
             Protokol, edge bulunduğunda agresif, edge yoksa pasif davranır.
Kural K270: Her gün sonu capital, drawdown ve kelly_fraction güncellenir.
Kural K271: Eğer günlük hedef tutmazsa, sonraki gün risk azaltılır (time_decay + halving).

Usage:
    from strategy.protocol_strategies.omega_protocol import OmegaProtocol
    omega = OmegaProtocol(initial_capital=1000)
    signal = omega.evaluate(df, symbol="THYAO")
    if signal:
        print(f"Omega Signal: {signal.side} {signal.size} @ {signal.entry_price}")
"""

import os
import sys
import time
import math
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
from agents.agent_council import AgentCouncil, Vote, ConsensusType
from agents.manipulation_detector import ManipulationDetector, ManipulationPattern
from adapters.worldmonitor_bridge import WorldMonitorBridge
from risk.execution_laws import ImmutableExecutionLawEngine
from risk.black_swan_guard import BlackSwanGuard
from data.unified_market_calendar import UnifiedMarketCalendar
from hermes_adapter.risk_gates import RiskGateEngine
from hermes_adapter.skill_engine import SkillEngine
from openclaw_adapter.agent_router import OpenClawRouter
from common.shared_experience_memory import SharedExperienceMemory
from strategy.portfolio_orchestrator import PortfolioOrchestrator
from strategy.dynamic_symbol_rotator import DynamicSymbolRotator
from strategy.ensemble_optimizer import EnsembleOptimizer


class OmegaStatus(Enum):
    PASS = "PASS"
    BLOCK = "BLOCK"
    WAIT = "WAIT"
    HALT = "HALT"


@dataclass
class PipelineConfig:
    """Toggle each subsystem on/off for flexibility / speed / debugging."""
    enable_worldmonitor: bool = True
    enable_black_swan: bool = True
    enable_calendar: bool = True
    enable_manipulation: bool = True
    enable_symbol_rotation: bool = False  # expensive, off by default
    enable_alpha_protocol: bool = True
    enable_compound_growth: bool = True
    enable_skill_engine: bool = True
    enable_shared_memory: bool = True
    enable_portfolio: bool = True
    enable_agent_council: bool = True
    enable_risk_gate: bool = True
    enable_immutable_laws: bool = True
    enable_ensemble: bool = True
    enable_openclaw: bool = True


@dataclass
class OmegaSignal:
    symbol: str
    side: str
    setup: str
    entry_price: float
    stop_loss: float
    take_profit: float
    size: float
    risk_pct: float
    rr: float
    confidence: float
    kelly_fraction: float
    compound_factor: float
    recovery_multiplier: float
    expected_return: float
    time_decay: float
    regime: str
    reasons: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    valid: bool = True

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "setup": self.setup,
            "entry_price": round(self.entry_price, 4),
            "stop_loss": round(self.stop_loss, 4),
            "take_profit": round(self.take_profit, 4),
            "size": round(self.size, 4),
            "risk_pct": round(self.risk_pct, 4),
            "rr": round(self.rr, 2),
            "confidence": round(self.confidence, 1),
            "kelly_fraction": round(self.kelly_fraction, 4),
            "compound_factor": round(self.compound_factor, 4),
            "recovery_multiplier": round(self.recovery_multiplier, 4),
            "expected_return": round(self.expected_return, 4),
            "time_decay": round(self.time_decay, 4),
            "regime": self.regime,
            "reasons": self.reasons,
            "timestamp": self.timestamp,
            "valid": self.valid,
        }


@dataclass
class PipelineResult:
    status: OmegaStatus
    step: str
    reason: str
    signal: Optional[OmegaSignal] = None
    context: Dict[str, Any] = field(default_factory=dict)


class OmegaProtocol:
    """
    Omega Protocol v1.0 — The Final Unified Strategy.

    Pipeline (16 steps, any BLOCK/WAIT/HALT aborts):
    1. WorldMonitor halt check
    2. BlackSwanGuard
    3. UnifiedMarketCalendar
    4. ManipulationDetector
    5. DynamicSymbolRotator (select best symbol if scanning)
    6. AlphaProtocol signal generation
    7. CompoundGrowthProtocol position sizing (Kelly)
    8. SkillEngine best-skill query
    9. SharedExperienceMemory lessons
    10. PortfolioOrchestrator allocation
    11. AgentCouncil meeting (consensus)
    12. Hermes RiskGateEngine
    13. ImmutableExecutionLawEngine
    14. EnsembleOptimizer regime weights
    15. OpenClawRouter final routing
    16. OmegaSignal assembly
    """

    PARAMS = {
        "initial_capital": 1_000.0,
        "target_capital": 1_000_000.0,
        "max_days": 20,
        "max_daily_loss_pct": 3.0,
        "max_drawdown_pct": 10.0,
        "kelly_cap": 0.25,
        "recovery_factor": 0.5,
        "recovery_max_mult": 1.5,
        "compound_mode": True,
        "session_hours": 8.5,
        "required_confidence": 70.0,
        "max_trades_per_day": 10,
        "target_daily_return": 0.412,  # 41.2% for 20-day 1000x
    }

    def __init__(self, initial_capital: float = 1_000.0, params: Optional[Dict] = None):
        self.params = {**self.PARAMS, **(params or {})}
        self.params["initial_capital"] = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        self.daily_pnl = 0.0
        self.total_days = 0
        self.trade_count_today = 0
        self.trade_history: List[dict] = []
        self._last_reset_day = datetime.now().day
        self._drawdown = 0.0

        # Subsystems
        self.alpha_proto = AlphaProtocol(account_size=initial_capital)
        self.compound_proto = CompoundGrowthProtocol(initial_capital=initial_capital)
        self.council = AgentCouncil(consensus=ConsensusType.SUPER_MAJORITY)
        self.manip_detector = ManipulationDetector()
        self.worldmonitor = WorldMonitorBridge()
        self.black_swan = BlackSwanGuard()
        self.calendar = UnifiedMarketCalendar()
        self.risk_gate = RiskGateEngine()
        self.skill_engine = SkillEngine()
        self.openclaw = OpenClawRouter()
        self.law_engine = ImmutableExecutionLawEngine(strict_mode=True)
        self.shared_memory = SharedExperienceMemory()
        self.portfolio = PortfolioOrchestrator(total_capital=initial_capital)
        self.rotator = DynamicSymbolRotator()
        self.ensemble = EnsembleOptimizer()

        # Register OpenClaw agents
        self.openclaw.register_agent("signal", lambda p: {"agent": "signal", "payload": p})
        self.openclaw.register_agent("risk", lambda p: {"agent": "risk", "payload": p})
        self.openclaw.register_agent("strategy", lambda p: {"agent": "strategy", "payload": p})
        self.openclaw.map_channel("internal", "strategy")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def evaluate(
        self,
        df: pd.DataFrame,
        symbol: str,
        venue: str = "BIST",
        timeframe: str = "M15",
        higher_tf_df: Optional[pd.DataFrame] = None,
        macro: Optional[dict] = None,
        p_win: float = 0.55,
        avg_win: float = 2.0,
        avg_loss: float = 1.0,
        last_pnl_pct: float = 0.0,
        scan_mode: bool = False,
        symbols: Optional[List[str]] = None,
        config: Optional[PipelineConfig] = None,
    ) -> Optional[OmegaSignal]:
        """
        Run full Omega pipeline. Returns OmegaSignal if ALL gates PASS.
        If scan_mode=True, uses DynamicSymbolRotator to pick best symbol.
        Use config to toggle subsystems on/off for speed or debugging.
        """
        cfg = config or PipelineConfig()

        # --- Step 0: Daily reset ---
        now = datetime.now()
        if now.day != self._last_reset_day:
            self._daily_reset()

        # --- Step 1: WorldMonitor halt ---
        if cfg.enable_worldmonitor:
            res = self._step_worldmonitor(symbol)
            if res.status != OmegaStatus.PASS:
                self._record_block(res)
                return None

        # --- Step 2: BlackSwanGuard ---
        if cfg.enable_black_swan:
            res = self._step_blackswan(df, symbol)
            if res.status != OmegaStatus.PASS:
                self._record_block(res)
                return None

        # --- Step 3: Market calendar ---
        if cfg.enable_calendar:
            res = self._step_calendar(venue)
            if res.status != OmegaStatus.PASS:
                self._record_block(res)
                return None

        # --- Step 4: Manipulation detection ---
        if cfg.enable_manipulation:
            res = self._step_manipulation(df, symbol)
            if res.status != OmegaStatus.PASS:
                self._record_block(res)
                return None

        # --- Step 5: Dynamic symbol rotation (optional) ---
        if cfg.enable_symbol_rotation and scan_mode and symbols:
            best = self._step_symbol_rotation(symbols)
            if best and best != symbol.upper():
                symbol = best
                self._log_reason(f"Rotated to best symbol: {symbol}")

        # --- Step 6: AlphaProtocol signal ---
        if not cfg.enable_alpha_protocol:
            return None
        alpha_signal = self.alpha_proto.evaluate(df, symbol=symbol, venue=venue, timeframe=timeframe, higher_tf_df=higher_tf_df, macro=macro)
        if alpha_signal is None:
            self._record_block(PipelineResult(OmegaStatus.BLOCK, "alpha_protocol", "No alpha signal"))
            return None

        # --- Step 7: CompoundGrowthProtocol sizing ---
        if cfg.enable_compound_growth:
            growth_signal = self._step_compound_growth(
                df, symbol, venue, higher_tf_df, p_win, avg_win, avg_loss, last_pnl_pct
            )
        else:
            from strategy.protocol_strategies.compound_growth_protocol import GrowthSignal
            growth_signal = GrowthSignal(
                symbol=alpha_signal.symbol,
                side=alpha_signal.side,
                setup=alpha_signal.setup,
                entry_price=alpha_signal.entry_price,
                stop_loss=alpha_signal.stop_loss,
                take_profit=alpha_signal.take_profit,
                size=alpha_signal.size,
                risk_pct=alpha_signal.risk_pct,
                rr=alpha_signal.rr,
                confidence=alpha_signal.confidence,
                timeframe=alpha_signal.timeframe,
                reasons=alpha_signal.reasons,
                kelly_fraction=0.1,
                compound_factor=1.0,
                recovery_multiplier=1.0,
                time_decay=1.0,
                expected_return=0.05,
            )
        if growth_signal is None:
            self._record_block(PipelineResult(OmegaStatus.BLOCK, "compound_growth", "Sizing blocked"))
            return None

        # --- Step 8: SkillEngine ---
        if cfg.enable_skill_engine:
            res = self._step_skill_engine(symbol, alpha_signal.setup.value)
            if res.status != OmegaStatus.PASS:
                self._record_block(res)
                return None

        # --- Step 9: SharedExperienceMemory ---
        if cfg.enable_shared_memory:
            res = self._step_shared_memory(symbol, alpha_signal.setup.value)
            if res.status != OmegaStatus.PASS:
                self._record_block(res)
                return None

        # --- Step 10: PortfolioOrchestrator ---
        alloc = self._step_portfolio(alpha_signal.setup.value) if cfg.enable_portfolio else {}

        # --- Step 11: AgentCouncil meeting ---
        if cfg.enable_agent_council:
            res = self._step_council(df, symbol, alpha_signal, macro)
            if res.status != OmegaStatus.PASS:
                self._record_block(res)
                return None

        # --- Step 12: Hermes RiskGateEngine ---
        if cfg.enable_risk_gate:
            res = self._step_risk_gate(symbol, growth_signal)
            if res.status != OmegaStatus.PASS:
                self._record_block(res)
                return None

        # --- Step 13: ImmutableExecutionLaws ---
        if cfg.enable_immutable_laws:
            res = self._step_laws(df, symbol, growth_signal)
            if res.status != OmegaStatus.PASS:
                self._record_block(res)
                return None

        # --- Step 14: EnsembleOptimizer ---
        regime = self._detect_regime(df)
        ensemble_weights = self.ensemble.regime_weights(regime, ["alpha", "compound", "momentum", "mean_reversion"]) if cfg.enable_ensemble else {}

        # --- Step 15: OpenClawRouter ---
        if cfg.enable_openclaw:
            route_res = self.openclaw.route("internal", "strategy", {
                "symbol": symbol,
                "side": alpha_signal.side,
                "confidence": alpha_signal.confidence,
            })
            if not route_res.get("ok"):
                self._record_block(PipelineResult(OmegaStatus.BLOCK, "openclaw", route_res.get("error", "Routing failed")))
                return None

        # --- Step 16: Assemble OmegaSignal ---
        omega = OmegaSignal(
            symbol=symbol,
            side=alpha_signal.side,
            setup=alpha_signal.setup.value,
            entry_price=alpha_signal.entry_price,
            stop_loss=alpha_signal.stop_loss,
            take_profit=alpha_signal.take_profit,
            size=growth_signal.size,
            risk_pct=growth_signal.risk_pct,
            rr=alpha_signal.rr,
            confidence=alpha_signal.confidence,
            kelly_fraction=growth_signal.kelly_fraction,
            compound_factor=growth_signal.compound_factor,
            recovery_multiplier=growth_signal.recovery_multiplier,
            expected_return=growth_signal.expected_return,
            time_decay=growth_signal.time_decay,
            regime=regime,
            reasons=alpha_signal.reasons + [f"ensemble_weights={ensemble_weights}", f"alloc={alloc}"],
            context={
                "alpha": alpha_signal.to_dict(),
                "growth": growth_signal.to_dict(),
                "regime": regime,
                "ensemble": ensemble_weights,
                "portfolio_alloc": {k: v.weight for k, v in alloc.items()} if alloc else {},
            },
            valid=True,
        )

        self._log_reason(f"Omega PASS: {symbol} {omega.side} size={omega.size:.2f} kelly={omega.kelly_fraction:.2%} conf={omega.confidence:.0f}")
        return omega

    def run_campaign(
        self,
        symbols: List[str],
        bars_provider,  # callable(symbol) -> pd.DataFrame
        higher_tf_provider=None,
    ) -> Dict[str, Any]:
        """
        Run a full compound campaign over max_days.
        Returns final report dict.
        """
        start_capital = self.current_capital
        target = self.params["target_capital"]
        max_days = self.params["max_days"]
        daily_log = []

        for day in range(1, max_days + 1):
            if self.current_capital >= target:
                break
            if self._drawdown >= self.params["max_drawdown_pct"]:
                daily_log.append({"day": day, "status": "HALT", "reason": "Max drawdown reached"})
                break

            day_pnl = 0.0
            trades_today = 0
            required_return = self._compute_required_daily_return()

            for sym in symbols:
                try:
                    df = bars_provider(sym)
                    if df is None or len(df) < 20:
                        continue
                    hdf = higher_tf_provider(sym) if higher_tf_provider else None

                    # Determine p_win from skill engine history if available
                    skill = self.skill_engine.get_best_skill(sym)
                    p_win = skill.win_rate if skill else 0.55
                    avg_win = skill.avg_pnl if skill and skill.avg_pnl > 0 else 2.0
                    avg_loss = 1.0

                    last_pnl_pct = self.trade_history[-1].get("pnl_pct", 0.0) if self.trade_history else 0.0

                    signal = self.evaluate(
                        df, symbol=sym, higher_tf_df=hdf,
                        p_win=p_win, avg_win=avg_win, avg_loss=avg_loss,
                        last_pnl_pct=last_pnl_pct,
                    )
                    if signal:
                        # Simulate execution (caller should call execute_signal on orchestrator)
                        # Here we record the planned trade
                        day_pnl += signal.expected_return * self.current_capital
                        trades_today += 1
                        self.trade_count_today += 1
                        self.trade_history.append({
                            "day": day,
                            "symbol": sym,
                            "side": signal.side,
                            "size": signal.size,
                            "entry": signal.entry_price,
                            "sl": signal.stop_loss,
                            "tp": signal.take_profit,
                            "pnl_pct": signal.expected_return,
                            "kelly": signal.kelly_fraction,
                        })
                        if self.trade_count_today >= self.params["max_trades_per_day"]:
                            break
                except Exception as e:
                    continue

            # Update capital (simulated compounding)
            self.current_capital += day_pnl
            if self.current_capital > self.peak_capital:
                self.peak_capital = self.current_capital
            self._drawdown = (self.peak_capital - self.current_capital) / self.peak_capital * 100
            self.total_days = day

            daily_log.append({
                "day": day,
                "capital": round(self.current_capital, 2),
                "day_pnl": round(day_pnl, 2),
                "trades": trades_today,
                "drawdown_pct": round(self._drawdown, 2),
                "required_return_pct": round(required_return * 100, 2),
            })

        return {
            "initial_capital": start_capital,
            "final_capital": round(self.current_capital, 2),
            "target_capital": target,
            "days_elapsed": self.total_days,
            "return_multiple": round(self.current_capital / start_capital, 2) if start_capital > 0 else 0,
            "max_drawdown_pct": round(self._drawdown, 2),
            "total_trades": len(self.trade_history),
            "daily_log": daily_log,
        }

    # ------------------------------------------------------------------
    # Pipeline steps
    # ------------------------------------------------------------------
    def _step_worldmonitor(self, symbol: str) -> PipelineResult:
        try:
            halt, reason = self.worldmonitor.should_halt_trading()
            if halt:
                return PipelineResult(OmegaStatus.HALT, "worldmonitor", reason)
        except Exception as e:
            return PipelineResult(OmegaStatus.PASS, "worldmonitor", f"Check error: {e}")
        return PipelineResult(OmegaStatus.PASS, "worldmonitor", "OK")

    def _step_blackswan(self, df: pd.DataFrame, symbol: str) -> PipelineResult:
        if self.black_swan.is_halted():
            return PipelineResult(OmegaStatus.HALT, "black_swan", "Global halt active")
        if len(df) >= 40:
            alert = self.black_swan.check(df, symbol=symbol)
            if alert.is_black_swan and alert.level in ("CRITICAL", "EXTREME"):
                self.black_swan.halt(symbol)
                return PipelineResult(OmegaStatus.HALT, "black_swan", alert.reason)
        return PipelineResult(OmegaStatus.PASS, "black_swan", "OK")

    def _step_calendar(self, venue: str) -> PipelineResult:
        if not self.calendar.is_market_open(venue):
            reason = self.calendar.get_reason(venue)
            return PipelineResult(OmegaStatus.HALT, "calendar", f"Market closed: {reason}")
        return PipelineResult(OmegaStatus.PASS, "calendar", "Open")

    def _step_manipulation(self, df: pd.DataFrame, symbol: str) -> PipelineResult:
        if len(df) < 20:
            return PipelineResult(OmegaStatus.WAIT, "manipulation", "Insufficient data")
        res = self.manip_detector.analyze(df, symbol=symbol)
        if res.is_manipulated and res.score >= 70:
            return PipelineResult(OmegaStatus.BLOCK, "manipulation", f"{res.pattern.value} score={res.score:.0f}")
        return PipelineResult(OmegaStatus.PASS, "manipulation", f"Score={res.score:.0f} OK")

    def _step_symbol_rotation(self, symbols: List[str]) -> Optional[str]:
        try:
            self.rotator.update_scores(symbols)
            best = self.rotator.select_best_symbol()
            return best.upper() if best else None
        except Exception:
            return None

    def _step_compound_growth(
        self,
        df: pd.DataFrame,
        symbol: str,
        venue: str,
        higher_tf_df: Optional[pd.DataFrame],
        p_win: float,
        avg_win: float,
        avg_loss: float,
        last_pnl_pct: float,
    ) -> Optional[GrowthSignal]:
        # Sync compound proto capital with omega capital
        self.compound_proto.current_capital = self.current_capital
        self.compound_proto.peak_capital = self.peak_capital
        self.compound_proto._drawdown = self._drawdown / 100.0
        self.compound_proto.total_days = self.total_days
        self.compound_proto.daily_pnl = self.daily_pnl

        signal = self.compound_proto.evaluate(
            df, symbol=symbol, venue=venue, higher_tf_df=higher_tf_df,
            p_win=p_win, avg_win=avg_win, avg_loss=avg_loss,
            last_pnl_pct=last_pnl_pct,
        )
        return signal

    def _step_skill_engine(self, symbol: str, setup: str) -> PipelineResult:
        skill = self.skill_engine.get_best_skill(symbol, min_confidence=50.0)
        if skill and skill.confidence >= self.params["required_confidence"]:
            return PipelineResult(OmegaStatus.PASS, "skill_engine", f"Best skill {skill.setup} conf={skill.confidence:.0f}")
        # No strong skill is not a blocker, just info
        return PipelineResult(OmegaStatus.PASS, "skill_engine", "No high-confidence skill")

    def _step_shared_memory(self, symbol: str, setup: str) -> PipelineResult:
        recs = self.shared_memory.query(symbol=symbol, min_outcome=-0.1, max_age_seconds=7*86400, limit=50)
        if recs:
            bad = [r for r in recs if r.outcome < 0]
            if len(bad) >= 3:
                return PipelineResult(OmegaStatus.WAIT, "shared_memory", f"{len(bad)} recent bad experiences")
        return PipelineResult(OmegaStatus.PASS, "shared_memory", "OK")

    def _step_portfolio(self, strategy_name: str) -> Dict[str, Any]:
        try:
            alloc = self.portfolio.allocate([{
                "name": strategy_name,
                "sharpe": 1.5,
                "recent_pnl": self.daily_pnl,
                "volatility": 0.02,
            }])
            return alloc
        except Exception:
            return {}

    def _step_council(
        self,
        df: pd.DataFrame,
        symbol: str,
        alpha_signal: AlphaSignal,
        macro: Optional[dict],
    ) -> PipelineResult:
        news_sentiment = None
        try:
            news_sentiment = self.worldmonitor.get_market_sentiment(symbol)
        except Exception:
            pass

        council_result = self.council.hold_meeting(
            symbol=symbol,
            signal={
                "side": alpha_signal.side,
                "confidence": alpha_signal.confidence,
                "setup": alpha_signal.setup.value,
                "entry": alpha_signal.entry_price,
                "sl": alpha_signal.stop_loss,
                "tp": alpha_signal.take_profit,
            },
            df=df,
            macro=macro,
            news_sentiment=news_sentiment,
        )
        if council_result.decision == Vote.BLOCK:
            return PipelineResult(OmegaStatus.BLOCK, "agent_council", f"BLOCK conf={council_result.confidence:.0f}")
        if council_result.decision == Vote.WAIT:
            return PipelineResult(OmegaStatus.WAIT, "agent_council", f"WAIT conf={council_result.confidence:.0f}")
        return PipelineResult(OmegaStatus.PASS, "agent_council", f"{council_result.decision.value} conf={council_result.confidence:.0f}")

    def _step_risk_gate(self, symbol: str, growth_signal: GrowthSignal) -> PipelineResult:
        ok, reasons = self.risk_gate.check_all(
            symbol=symbol,
            size=growth_signal.size,
            price=growth_signal.entry_price,
            side=growth_signal.side,
            confidence=growth_signal.confidence,
            sl=growth_signal.stop_loss,
            tp=growth_signal.take_profit,
            open_positions=len(self.trade_history),
            portfolio_value=self.current_capital,
        )
        if not ok:
            return PipelineResult(OmegaStatus.BLOCK, "risk_gate", "; ".join(reasons))
        return PipelineResult(OmegaStatus.PASS, "risk_gate", "OK")

    def _step_laws(self, df: pd.DataFrame, symbol: str, growth_signal: GrowthSignal) -> PipelineResult:
        law_signal = {
            "symbol": symbol,
            "side": growth_signal.side,
            "size": growth_signal.size,
            "price": growth_signal.entry_price,
            "confidence": growth_signal.confidence,
            "atr_pct": growth_signal.context.get("atr_pct", 0.0) if hasattr(growth_signal, "context") else 0.0,
            "spread_pct": 0.0,
            "leverage": 1.0,
            "prob_win": growth_signal.context.get("prob_win", 0.5) if hasattr(growth_signal, "context") else 0.5,
            "fake_breakout_prob": 0.0,
            "liquidation_risk": 0.0,
            "stale_order_seconds": 0.0,
        }
        law_state = {
            "equity": self.current_capital,
            "portfolio_heat": len(self.trade_history) * 0.01,
            "ws_latency_ms": 0.0,
            "uncertainty_score": 0.0,
            "replay_match_score": 1.0,
        }
        verdict = self.law_engine.check(law_signal, state=law_state)
        if not verdict.allowed:
            return PipelineResult(OmegaStatus.BLOCK, "immutable_laws", "; ".join(verdict.reasons))
        return PipelineResult(OmegaStatus.PASS, "immutable_laws", "OK")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _compute_required_daily_return(self) -> float:
        P = self.current_capital
        A = self.params["target_capital"]
        t = self.params["max_days"] - self.total_days
        if t <= 0 or P <= 0:
            return 0.0
        return (A / P) ** (1.0 / t) - 1.0

    def _detect_regime(self, df: pd.DataFrame) -> str:
        if len(df) < 50:
            return "sideways"
        close = df["close"]
        ema20 = close.ewm(span=20).mean().iloc[-1]
        ema50 = close.ewm(span=50).mean().iloc[-1]
        last = close.iloc[-1]
        if last > ema20 > ema50:
            return "bull"
        elif last < ema20 < ema50:
            return "bear"
        return "sideways"

    def _daily_reset(self):
        self.daily_pnl = 0.0
        self.trade_count_today = 0
        self._last_reset_day = datetime.now().day
        self.risk_gate.reset_daily()

    def _record_block(self, res: PipelineResult):
        self.shared_memory.record_block(
            agent=res.step,
            symbol=res.context.get("symbol", "UNKNOWN"),
            reason=res.reason,
            context={"step": res.step, "status": res.status.value},
        )

    def _log_reason(self, msg: str):
        self.trade_history.append({"log": msg, "time": time.time()})


if __name__ == "__main__":
    # Demo
    omega = OmegaProtocol(initial_capital=1000)
    print(f"Omega initialized. Target: {omega.params['target_capital']:,.0f} in {omega.params['max_days']} days")
    print(f"Required daily return: {omega._compute_required_daily_return()*100:.1f}%")

    df = pd.DataFrame({
        "open": [100.0]*30,
        "high": [101.0]*30,
        "low": [99.0]*30,
        "close": [100.0]*30,
        "volume": [1000]*30,
    })
    sig = omega.evaluate(df, symbol="TEST")
    print("Signal:", sig.to_dict() if sig else None)
