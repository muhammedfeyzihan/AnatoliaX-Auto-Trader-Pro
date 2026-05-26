"""
integration_orchestrator.py — Unified Cross-Platform Integration Orchestrator

Wires together:
- NautilusTrader: deterministic low-latency execution core + replay engine
- Hummingbot: exchange/liquidity infrastructure + arbitrage
- OpenClaw: multi-agent routing + skill loading
- Hermes: risk gates + skill engine + TA pre-filter

Usage:
    from adapters.integration_orchestrator import IntegrationOrchestrator
    orch = IntegrationOrchestrator()
    orch.initialize()
    result = orch.execute_signal({"symbol": "THYAO", "side": "BUY", "size": 100})
    health = orch.health_check()
    replay = orch.replay_validate(ticks=[...], expected_state={...})
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

from adapters.nautilus_adapter import NautilusAdapter
from adapters.hummingbot_adapter import HummingbotAdapter
from adapters.worldmonitor_bridge import WorldMonitorBridge
from openclaw_adapter.agent_router import OpenClawRouter
from hermes_adapter.risk_gates import RiskGateEngine
from hermes_adapter.skill_engine import SkillEngine
from hermes_adapter.ta_filter import TAFPreFilter
from risk.execution_laws import ImmutableExecutionLawEngine
from risk.black_swan_guard import BlackSwanGuard
from common.shared_experience_memory import SharedExperienceMemory
from data.unified_market_calendar import UnifiedMarketCalendar
from agents.agent_council import AgentCouncil, Vote


@dataclass
class ExecutionResult:
    ok: bool
    order_id: Optional[str]
    symbol: str
    side: str
    size: float
    price: Optional[float]
    provider: str
    risk_checks: List[str] = field(default_factory=list)
    agent: str = ""
    liquidity: Optional[dict] = None
    error: str = ""
    timestamp: float = field(default_factory=time.time)


class IntegrationOrchestrator:
    """
    Master orchestrator for Nautilus + Hummingbot + OpenClaw + Hermes.

    Execution flow:
    1. Hermes TA pre-filter (cheap local indicators)
    2. Hermes RiskGateEngine (10 independent gates)
    3. OpenClawRouter (agent routing)
    4. NautilusAdapter (deterministic execution / replay)
    5. HummingbotAdapter (liquidity check + exchange fallback)
    """

    def __init__(
        self,
        venue: str = "BIST",
        exchange: str = "binance",
        enable_replay: bool = True,
        enable_arbitrage: bool = False,
        enable_market_making: bool = False,
    ):
        self.venue = venue
        self.exchange = exchange
        self.enable_replay = enable_replay
        self.enable_arbitrage = enable_arbitrage
        self.enable_market_making = enable_market_making

        # Subsystems
        self.nautilus: Optional[NautilusAdapter] = None
        self.hummingbot: Optional[HummingbotAdapter] = None
        self.router: Optional[OpenClawRouter] = None
        self.risk_gate: Optional[RiskGateEngine] = None
        self.skill_engine: Optional[SkillEngine] = None
        self.ta_filter: Optional[TAFPreFilter] = None
        self.law_engine: Optional[ImmutableExecutionLawEngine] = None
        self.black_swan_guard: Optional[BlackSwanGuard] = None
        self.shared_memory: Optional[SharedExperienceMemory] = None
        self.calendar: Optional[UnifiedMarketCalendar] = None
        self.worldmonitor: Optional[WorldMonitorBridge] = None
        self.agent_council: Optional[AgentCouncil] = None

        self._initialized = False
        self._execution_log: List[ExecutionResult] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def initialize(self) -> dict:
        """Initialize all subsystems. Returns status dict."""
        self.nautilus = NautilusAdapter(venue=self.venue)
        self.hummingbot = HummingbotAdapter(
            exchange=self.exchange,
            arbitrage_enabled=self.enable_arbitrage,
            market_making_enabled=self.enable_market_making,
        )
        self.router = OpenClawRouter()
        self.risk_gate = RiskGateEngine()
        self.skill_engine = SkillEngine()
        self.ta_filter = TAFPreFilter(threshold=65.0)
        self.law_engine = ImmutableExecutionLawEngine(strict_mode=True)
        self.black_swan_guard = BlackSwanGuard()
        self.shared_memory = SharedExperienceMemory()
        self.calendar = UnifiedMarketCalendar()
        self.worldmonitor = WorldMonitorBridge()
        self.agent_council = AgentCouncil()

        # Register default OpenClaw agent mappings
        self.router.map_channel("telegram", "strategy")
        self.router.map_channel("webhook", "signal")
        self.router.map_channel("internal", "strategy")

        # Register default agent handlers (passthrough for internal pipeline)
        self.router.register_agent("strategy", lambda payload: {"agent": "strategy", "routed": True, "payload": payload})
        self.router.register_agent("signal", lambda payload: {"agent": "signal", "routed": True, "payload": payload})
        self.router.register_agent("risk", lambda payload: {"agent": "risk", "routed": True, "payload": payload})

        self._initialized = True
        return self.health_check()

    def health_check(self) -> dict:
        """Check health of all subsystems."""
        if not self._initialized:
            return {"ok": False, "reason": "NOT_INITIALIZED"}

        return {
            "ok": True,
            "timestamp": time.time(),
            "nautilus": {
                "available": self.nautilus.is_available() if self.nautilus else False,
                "venue": self.venue,
            },
            "hummingbot": {
                "available": self.hummingbot.is_available() if self.hummingbot else False,
                "exchange": self.exchange,
                "arbitrage": self.enable_arbitrage,
                "market_making": self.enable_market_making,
            },
            "openclaw": {
                "agents": self.router.list_agents() if self.router else [],
                "channels": self.router.list_channels() if self.router else {},
            },
            "hermes": {
                "risk_gates_active": self.risk_gate is not None,
                "skill_count": self.skill_engine.get_skill_stats()["total_skills"] if self.skill_engine else 0,
            },
            "risk": {
                "execution_laws_active": self.law_engine is not None,
                "black_swan_guard_active": self.black_swan_guard is not None,
                "black_swan_halted": self.black_swan_guard.is_halted() if self.black_swan_guard else False,
            },
            "memory": {
                "shared_experience_active": self.shared_memory is not None,
                "total_records": self.shared_memory.stats()["total_records"] if self.shared_memory else 0,
            },
            "calendar": {
                "venue": self.venue,
                "is_open": self.calendar.is_market_open(self.venue) if self.calendar else False,
            },
            "worldmonitor": {
                "active": self.worldmonitor is not None,
                "news_count": len(self.worldmonitor._news_queue) if self.worldmonitor else 0,
                "macro_cached": self.worldmonitor.get_macro_snapshot() is not None if self.worldmonitor else False,
            },
            "agent_council": {
                "active": self.agent_council is not None,
                "consensus_type": self.agent_council.consensus.value if self.agent_council else None,
                "meeting_count": len(self.agent_council._meeting_history) if self.agent_council else 0,
            },
            "replay_enabled": self.enable_replay,
        }

    # ------------------------------------------------------------------
    # Execution pipeline
    # ------------------------------------------------------------------
    def execute_signal(
        self,
        signal: dict,
        macro: Optional[dict] = None,
        sentiment: float = 0.0,
        bars: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Execute a signal through the full pipeline.

        signal: {"symbol": str, "side": "BUY"|"SELL", "size": float, "price": float|None,
                  "sl": float, "tp": float, "confidence": float}
        """
        if not self._initialized:
            result = ExecutionResult(ok=False, error="Orchestrator not initialized", symbol=signal.get("symbol", ""), side=signal.get("side", ""), size=signal.get("size", 0.0), price=None, order_id=None, provider="none")
            self._execution_log.append(result)
            return result

        symbol = signal.get("symbol", "")
        side = signal.get("side", "")
        size = signal.get("size", 0.0)
        price = signal.get("price")
        confidence = signal.get("confidence", 0.0)
        sl = signal.get("sl", 0.0)
        tp = signal.get("tp", 0.0)

        # 0. Market calendar check
        if self.calendar and not self.calendar.is_market_open(self.venue):
            reason = self.calendar.get_reason(self.venue)
            result = ExecutionResult(
                ok=False, error=f"Market closed: {reason}",
                symbol=symbol, side=side, size=size, price=price,
                order_id=None, provider="market_calendar",
            )
            if self.shared_memory:
                self.shared_memory.record_block("calendar", symbol, reason, {"venue": self.venue})
            self._execution_log.append(result)
            return result

        # 1. Black Swan Guard (early halt)
        if self.black_swan_guard:
            if self.black_swan_guard.is_halted():
                result = ExecutionResult(
                    ok=False, error="Black swan halt active — execution suspended",
                    symbol=symbol, side=side, size=size, price=price,
                    order_id=None, provider="black_swan_guard",
                )
                self._execution_log.append(result)
                return result
            if bars and isinstance(bars, dict) and "close" in bars:
                import pandas as pd
                df = pd.DataFrame(bars)
                alert = self.black_swan_guard.check(df, symbol=symbol)
                if alert.is_black_swan and alert.level in ("CRITICAL", "EXTREME"):
                    self.black_swan_guard.halt(symbol)
                    result = ExecutionResult(
                        ok=False, error=f"Black swan detected: {alert.reason}",
                        symbol=symbol, side=side, size=size, price=price,
                        order_id=None, provider="black_swan_guard",
                    )
                    self._execution_log.append(result)
                    return result

        # 2. Hermes TA pre-filter (cheap local indicators)
        if bars and self.ta_filter:
            ta_res = self.ta_filter.evaluate(symbol, bars=bars)
            if not ta_res.confirmed:
                result = ExecutionResult(
                    ok=False, error=f"TA filter rejected: {ta_res.reason}",
                    symbol=symbol, side=side, size=size, price=price,
                    order_id=None, provider="hermes_ta_filter",
                )
                self._execution_log.append(result)
                return result

        # 3. Hermes RiskGateEngine
        open_positions = 0  # Could be fetched from portfolio
        portfolio_value = 100_000.0
        if self.risk_gate:
            ok, reasons = self.risk_gate.check_all(
                symbol=symbol,
                size=size,
                price=price or 0.0,
                side=side,
                confidence=confidence,
                sl=sl,
                tp=tp,
                open_positions=open_positions,
                portfolio_value=portfolio_value,
            )
            if not ok:
                result = ExecutionResult(
                    ok=False, error=f"Risk gate blocked: {'; '.join(reasons)}",
                    symbol=symbol, side=side, size=size, price=price,
                    order_id=None, provider="hermes_risk_gate",
                    risk_checks=reasons,
                )
                self._execution_log.append(result)
                return result

        # 4. Immutable Execution Laws (pre-trade guardian)
        if self.law_engine:
            # Gather market data for laws
            spread_pct = 0.0
            if self.hummingbot:
                try:
                    liq_snap = self.hummingbot.get_liquidity_snapshot(symbol)
                    spread_pct = liq_snap.spread_pct
                except Exception:
                    pass
            law_signal = {
                "symbol": symbol,
                "side": side,
                "size": size,
                "price": price,
                "confidence": confidence,
                "atr_pct": signal.get("atr_pct", 0.0),
                "spread_pct": spread_pct,
                "leverage": signal.get("leverage", 1.0),
                "prob_win": signal.get("prob_win", 0.5),
                "fake_breakout_prob": signal.get("fake_breakout_prob", 0.0),
                "liquidation_risk": signal.get("liquidation_risk", 0.0),
                "stale_order_seconds": signal.get("stale_order_seconds", 0.0),
            }
            law_state = {
                "equity": portfolio_value,
                "portfolio_heat": open_positions * 0.02,
                "ws_latency_ms": signal.get("ws_latency_ms", 0.0),
                "uncertainty_score": signal.get("uncertainty_score", 0.0),
                "replay_match_score": signal.get("replay_match_score", 1.0),
            }
            verdict = self.law_engine.check(law_signal, state=law_state)
            if not verdict.allowed:
                result = ExecutionResult(
                    ok=False, error=f"Immutable laws blocked: {'; '.join(verdict.reasons)}",
                    symbol=symbol, side=side, size=size, price=price,
                    order_id=None, provider="immutable_execution_laws",
                    risk_checks=verdict.reasons,
                )
                self._execution_log.append(result)
                return result

        # 5. Agent Council Meeting (Ruflo-inspired consensus)
        if self.agent_council:
            news_sentiment = self.worldmonitor.get_market_sentiment(symbol) if self.worldmonitor else None
            council_result = self.agent_council.hold_meeting(
                symbol=symbol,
                signal={"side": side, "confidence": confidence, "price": price, "sl": sl, "tp": tp},
                df=pd.DataFrame(bars) if bars and isinstance(bars, dict) else None,
                news_sentiment=news_sentiment,
            )
            if council_result.decision in (Vote.BLOCK, Vote.WAIT):
                result = ExecutionResult(
                    ok=False,
                    error=f"Agent Council blocked: {council_result.decision.value} (conf={council_result.confidence:.0f}%). Minutes: {council_result.minutes[:200]}...",
                    symbol=symbol, side=side, size=size, price=price,
                    order_id=None, provider="agent_council",
                    risk_checks=[f"council_{council_result.decision.value}"],
                )
                if self.shared_memory:
                    self.shared_memory.record_block(
                        agent="agent_council", symbol=symbol,
                        reason=f"Council voted {council_result.decision.value}",
                        context=council_result.to_dict(),
                    )
                self._execution_log.append(result)
                return result
            # Council approved — use its confidence
            confidence = council_result.confidence

        # 6. OpenClaw routing
        agent_id = "strategy"
        if self.router:
            route_res = self.router.route(
                channel="internal", intent=agent_id, payload=signal
            )
            if not route_res.get("ok"):
                result = ExecutionResult(
                    ok=False, error=f"OpenClaw routing failed: {route_res.get('error')}",
                    symbol=symbol, side=side, size=size, price=price,
                    order_id=None, provider="openclaw",
                    agent=agent_id,
                )
                self._execution_log.append(result)
                return result

        # 6. Nautilus execution (deterministic core)
        provider = "nautilus"
        order: dict = {}
        if self.nautilus:
            self.nautilus.register_symbol(symbol)
            if price:
                order = self.nautilus.place_limit_order(symbol, side, int(size), price)
            else:
                order = self.nautilus.place_market_order(symbol, side, int(size))
            if order.get("status") == "ERROR":
                # 7. Hummingbot fallback
                provider = "hummingbot"
                if self.hummingbot:
                    self.hummingbot.register_symbol(symbol)
                    if price:
                        order = self.hummingbot.place_limit_order(symbol, side, size, price)
                    else:
                        order = self.hummingbot.place_market_order(symbol, side, size)
                else:
                    result = ExecutionResult(
                        ok=False, error="Nautilus and Hummingbot both failed",
                        symbol=symbol, side=side, size=size, price=price,
                        order_id=None, provider="none",
                    )
                    self._execution_log.append(result)
                    return result
        else:
            result = ExecutionResult(
                ok=False, error="Nautilus adapter not initialized",
                symbol=symbol, side=side, size=size, price=price,
                order_id=None, provider="none",
            )
            self._execution_log.append(result)
            return result

        # Liquidity snapshot
        liq = None
        if self.hummingbot:
            liq = self.hummingbot.get_liquidity_snapshot(symbol).to_dict()

        result = ExecutionResult(
            ok=order.get("status") in ("FILLED", "OPEN"),
            order_id=order.get("order_id"),
            symbol=symbol,
            side=side,
            size=size,
            price=price,
            provider=provider,
            agent=agent_id,
            liquidity=liq,
            error=order.get("error", ""),
        )
        self._execution_log.append(result)

        # Skill learning
        if self.skill_engine:
            # Deferred: actual PnL would be reported later via report_outcome
            pass

        return result

    def report_outcome(self, symbol: str, setup: str, pnl: float, context: Optional[dict] = None):
        """Report trade outcome to Hermes skill engine and shared memory."""
        if self.skill_engine:
            outcome = "win" if pnl > 0 else "loss"
            self.skill_engine.learn(symbol=symbol, setup=setup, outcome=outcome, pnl=pnl)
        if self.shared_memory:
            self.shared_memory.record_experience(
                agent="integration_orchestrator",
                action=f"{setup}",
                symbol=symbol,
                outcome=pnl,
                context=context or {},
                tags=["trade_outcome", "win" if pnl > 0 else "loss", symbol.upper()],
            )

    # ------------------------------------------------------------------
    # Replay & determinism
    # ------------------------------------------------------------------
    def replay_validate(self, ticks: list[dict], expected_state: dict, tolerance: float = 1e-9) -> dict:
        """
        Run deterministic replay through Nautilus and validate state.
        """
        if not self.nautilus:
            return {"valid": False, "error": "Nautilus not initialized"}

        session = self.nautilus.replay_start(ticks, initial_state=expected_state.get("initial"))
        while True:
            event = self.nautilus.replay_step()
            if event is None:
                break
        validation = self.nautilus.replay_validate(expected_state, tolerance=tolerance)
        validation["session_id"] = session.get("session_id")
        validation["checksum"] = self.nautilus.state_checksum()
        return validation

    def get_execution_log(self) -> List[ExecutionResult]:
        return list(self._execution_log)

    def clear_execution_log(self):
        self._execution_log.clear()

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    def scan_arbitrage(self, symbol: str, min_spread_pct: float = 0.5) -> List[dict]:
        if not self.hummingbot:
            return []
        ops = self.hummingbot.scan_arbitrage(symbol, min_spread_pct=min_spread_pct)
        return [op.__dict__ for op in ops]

    def get_best_skill(self, symbol: str, min_confidence: float = 50.0) -> Optional[dict]:
        if not self.skill_engine:
            return None
        skill = self.skill_engine.get_best_skill(symbol, min_confidence=min_confidence)
        return skill.to_dict() if skill else None

    def run_compound_growth_protocol(
        self,
        df: dict,
        symbol: str,
        initial_capital: float = 1_000.0,
        higher_tf_df: Optional[dict] = None,
        p_win: float = 0.55,
        avg_win: float = 2.0,
        avg_loss: float = 1.0,
        last_pnl_pct: float = 0.0,
    ) -> dict:
        """Run Compound Growth Protocol with Kelly Criterion + auto-execution."""
        import pandas as pd
        from strategy.protocol_strategies.compound_growth_protocol import CompoundGrowthProtocol

        pdf = pd.DataFrame(df)
        hdf = pd.DataFrame(higher_tf_df) if higher_tf_df else None
        proto = CompoundGrowthProtocol(initial_capital=initial_capital)

        # Inject WorldMonitor macro context if available
        macro_context = {}
        if self.worldmonitor:
            macro = self.worldmonitor.get_macro_snapshot()
            composite = self.worldmonitor.get_market_composite()
            if macro:
                macro_context["usd_try"] = macro.usd_try
                macro_context["vix"] = macro.vix
                macro_context["bist100_change"] = macro.bist100_change_pct
            if composite:
                macro_context["composite_score"] = composite.score
                macro_context["regime"] = composite.regime

        signal = proto.evaluate(
            pdf, symbol=symbol, venue=self.venue, higher_tf_df=hdf,
            p_win=p_win, avg_win=avg_win, avg_loss=avg_loss,
            last_pnl_pct=last_pnl_pct,
        )
        if not signal:
            return {"ok": False, "reason": "No signal from Compound Growth Protocol", "symbol": symbol, "capital": proto.current_capital}

        # Check WorldMonitor halt before execution
        if self.worldmonitor:
            halt, reason = self.worldmonitor.should_halt_trading()
            if halt:
                return {"ok": False, "reason": f"WorldMonitor halt: {reason}", "symbol": symbol, "capital": proto.current_capital}

        exec_result = self.execute_signal(
            signal={
                "symbol": signal.symbol,
                "side": signal.side,
                "size": signal.size,
                "price": signal.entry_price,
                "sl": signal.stop_loss,
                "tp": signal.take_profit,
                "confidence": signal.confidence,
                "setup": signal.setup.value,
                "kelly": signal.kelly_fraction,
            },
            bars=df,
        )
        if self.shared_memory:
            if exec_result.ok:
                self.shared_memory.record_experience(
                    agent="compound_growth",
                    action=f"EXECUTED {signal.side} Kelly={signal.kelly_fraction:.2%}",
                    symbol=symbol,
                    outcome=0.0,
                    context={**signal.to_dict(), **macro_context},
                    tags=["compound_growth", "kelly", signal.side, symbol.upper()],
                )
            else:
                self.shared_memory.record_block(
                    agent="compound_growth", symbol=symbol,
                    reason=exec_result.error,
                    context={**signal.to_dict(), **macro_context},
                )
        return {
            "ok": exec_result.ok,
            "signal": signal.to_dict(),
            "capital": proto.current_capital,
            "capital_ratio": round(proto.current_capital / initial_capital, 2),
            "execution": {
                "order_id": exec_result.order_id,
                "provider": exec_result.provider,
                "error": exec_result.error,
            },
        }

    def run_alpha_protocol(
        self,
        df: dict,
        symbol: str,
        higher_tf_df: Optional[dict] = None,
    ) -> dict:
        """Run Alpha Protocol strategy and auto-execute if signal passes all gates."""
        import pandas as pd
        from strategy.protocol_strategies.alpha_protocol import AlphaProtocol

        pdf = pd.DataFrame(df)
        hdf = pd.DataFrame(higher_tf_df) if higher_tf_df else None
        proto = AlphaProtocol(account_size=100_000.0)
        signal = proto.evaluate(pdf, symbol=symbol, venue=self.venue, higher_tf_df=hdf)
        if not signal:
            return {"ok": False, "reason": "No signal from Alpha Protocol", "symbol": symbol}

        exec_result = self.execute_signal(
            signal={
                "symbol": signal.symbol,
                "side": signal.side,
                "size": signal.size,
                "price": signal.entry_price,
                "sl": signal.stop_loss,
                "tp": signal.take_profit,
                "confidence": signal.confidence,
                "setup": signal.setup.value,
            },
            bars=df,
        )
        if self.shared_memory:
            if exec_result.ok:
                self.shared_memory.record_experience(
                    agent="alpha_protocol",
                    action=f"EXECUTED {signal.side} {signal.setup.value}",
                    symbol=symbol,
                    outcome=0.0,
                    context=signal.to_dict(),
                    tags=["alpha_protocol", "executed", signal.side, symbol.upper()],
                )
            else:
                self.shared_memory.record_block(
                    agent="alpha_protocol", symbol=symbol,
                    reason=exec_result.error,
                    context=signal.to_dict(),
                )
        return {
            "ok": exec_result.ok,
            "signal": signal.to_dict(),
            "execution": {
                "order_id": exec_result.order_id,
                "provider": exec_result.provider,
                "error": exec_result.error,
            },
        }

    def run_omega_protocol(
        self,
        df: dict,
        symbol: str,
        higher_tf_df: Optional[dict] = None,
        p_win: float = 0.55,
        avg_win: float = 2.0,
        avg_loss: float = 1.0,
        last_pnl_pct: float = 0.0,
    ) -> dict:
        """Run Omega Protocol (full 16-step pipeline) and auto-execute if signal passes ALL gates."""
        import pandas as pd
        from strategy.protocol_strategies.omega_protocol import OmegaProtocol

        pdf = pd.DataFrame(df)
        hdf = pd.DataFrame(higher_tf_df) if higher_tf_df else None
        proto = OmegaProtocol(initial_capital=1_000.0)
        signal = proto.evaluate(
            pdf, symbol=symbol, venue=self.venue, higher_tf_df=hdf,
            p_win=p_win, avg_win=avg_win, avg_loss=avg_loss,
            last_pnl_pct=last_pnl_pct,
        )
        if not signal:
            return {"ok": False, "reason": "No signal from Omega Protocol", "symbol": symbol}

        # Inject macro from WorldMonitor if available
        macro_context = {}
        if self.worldmonitor:
            macro = self.worldmonitor.get_macro_snapshot()
            composite = self.worldmonitor.get_market_composite()
            if macro:
                macro_context["usd_try"] = macro.usd_try
                macro_context["vix"] = macro.vix
            if composite:
                macro_context["composite_score"] = composite.score
                macro_context["regime"] = composite.regime

        exec_result = self.execute_signal(
            signal={
                "symbol": signal.symbol,
                "side": signal.side,
                "size": signal.size,
                "price": signal.entry_price,
                "sl": signal.stop_loss,
                "tp": signal.take_profit,
                "confidence": signal.confidence,
                "setup": signal.setup,
                "kelly": signal.kelly_fraction,
            },
            bars=df,
            macro=macro_context,
        )
        if self.shared_memory:
            if exec_result.ok:
                self.shared_memory.record_experience(
                    agent="omega_protocol",
                    action=f"EXECUTED {signal.side} Kelly={signal.kelly_fraction:.2%}",
                    symbol=symbol,
                    outcome=0.0,
                    context={**signal.to_dict(), **macro_context},
                    tags=["omega_protocol", "executed", signal.side, symbol.upper()],
                )
            else:
                self.shared_memory.record_block(
                    agent="omega_protocol", symbol=symbol,
                    reason=exec_result.error,
                    context={**signal.to_dict(), **macro_context},
                )
        return {
            "ok": exec_result.ok,
            "signal": signal.to_dict(),
            "capital": proto.current_capital,
            "capital_ratio": round(proto.current_capital / proto.params["initial_capital"], 2),
            "execution": {
                "order_id": exec_result.order_id,
                "provider": exec_result.provider,
                "error": exec_result.error,
            },
        }

    def run_omega_campaign(
        self,
        symbols: List[str],
        bars_provider,  # callable(symbol) -> pd.DataFrame
        higher_tf_provider=None,
    ) -> dict:
        """Run full Omega compound campaign over max_days."""
        from strategy.protocol_strategies.omega_protocol import OmegaProtocol
        proto = OmegaProtocol(initial_capital=1_000.0)
        report = proto.run_campaign(symbols, bars_provider, higher_tf_provider)
        return report

    def run_tiered_protocol(
        self,
        df: dict,
        symbol: str,
        tier: str = "PCT_5",
        higher_tf_df: Optional[dict] = None,
    ) -> dict:
        """Run Tiered Growth Protocol with specified daily return target tier."""
        import pandas as pd
        from strategy.protocol_strategies.tiered_growth_protocol import TieredGrowthProtocol, DailyReturnTarget

        pdf = pd.DataFrame(df)
        hdf = pd.DataFrame(higher_tf_df) if higher_tf_df else None
        target = DailyReturnTarget[tier.upper()] if hasattr(DailyReturnTarget, tier.upper()) else DailyReturnTarget.PCT_5
        proto = TieredGrowthProtocol(initial_capital=10_000.0, target=target)
        result = proto.evaluate(pdf, symbol=symbol, venue=self.venue, higher_tf_df=hdf)
        if not result:
            return {"ok": False, "reason": f"No signal from Tiered Protocol ({tier})", "symbol": symbol, "tier": tier}

        signal_raw = result.get("signal", {})
        exec_result = self.execute_signal(
            signal={
                "symbol": symbol,
                "side": signal_raw.get("side", "BUY"),
                "size": signal_raw.get("size", 0.0),
                "price": signal_raw.get("entry_price", 0.0),
                "sl": signal_raw.get("stop_loss", 0.0),
                "tp": signal_raw.get("take_profit", 0.0),
                "confidence": signal_raw.get("confidence", 50.0),
                "setup": signal_raw.get("setup", "MOMENTUM"),
            },
            bars=df,
        )
        if self.shared_memory:
            if exec_result.ok:
                self.shared_memory.record_experience(
                    agent="tiered_protocol",
                    action=f"EXECUTED {tier} {signal_raw.get('side', '')}",
                    symbol=symbol,
                    outcome=0.0,
                    context={**result},
                    tags=["tiered_protocol", tier, signal_raw.get("side", ""), symbol.upper()],
                )
            else:
                self.shared_memory.record_block(
                    agent="tiered_protocol", symbol=symbol,
                    reason=exec_result.error,
                    context={**result},
                )
        return {
            "ok": exec_result.ok,
            "tier": tier,
            "signal": signal_raw,
            "projection": result.get("monthly_projection", {}),
            "execution": {
                "order_id": exec_result.order_id,
                "provider": exec_result.provider,
                "error": exec_result.error,
            },
        }

    def run_tiered_scan(
        self,
        symbols: List[str],
        tier: str = "PCT_5",
        bars_provider=None,
    ) -> List[dict]:
        """Scan multiple symbols with Tiered Protocol."""
        import pandas as pd
        from strategy.protocol_strategies.tiered_growth_protocol import TieredGrowthProtocol, DailyReturnTarget

        target = DailyReturnTarget[tier.upper()] if hasattr(DailyReturnTarget, tier.upper()) else DailyReturnTarget.PCT_5
        proto = TieredGrowthProtocol(initial_capital=10_000.0, target=target)
        results = []
        for sym in symbols:
            try:
                df = bars_provider(sym) if bars_provider else None
                if df is None or len(df) < 20:
                    continue
                res = proto.evaluate(df, symbol=sym, venue=self.venue)
                if res:
                    results.append({"symbol": sym, "tier": tier, **res})
            except Exception:
                continue
        return results


if __name__ == "__main__":
    orch = IntegrationOrchestrator()
    status = orch.initialize()
    print("Health:", status)
    res = orch.execute_signal({
        "symbol": "THYAO",
        "side": "BUY",
        "size": 100,
        "price": 105.0,
        "confidence": 75.0,
        "sl": 100.0,
        "tp": 115.0,
    })
    print("Execution:", res)
    replay = orch.replay_validate(
        ticks=[{"timestamp": "2026-01-01T00:00:00", "price": 100.0, "volume": 1000}],
        expected_state={"cash": 100_000.0},
    )
    print("Replay:", replay)
