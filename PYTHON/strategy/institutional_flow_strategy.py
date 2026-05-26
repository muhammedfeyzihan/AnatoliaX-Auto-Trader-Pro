"""
strategy/institutional_flow_strategy.py — Institutional-Grade Flow Strategy (v4.0)
Fixed to handle column name differences (price vs close).
"""

import time
import hashlib
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from collections import deque
import json

import pandas as pd
import numpy as np

# Core imports
from common.event_sourcing import EventStore, EventBus, Event, EventType
from common.async_event_bus import AsyncEventBus
from data.data_quality_layer import DataQualityLayer, DataType, QualityLevel, DataQualityReport
from observability.opentelemetry_tracing import DistributedTracingPipeline, SpanKind, StatusCode
from infrastructure.messaging_backbone import ExactlyOnceMessagingBackbone
from agents.agent_council import AgentCouncil, ConsensusType, Vote
from agents.ai_regime_detector import AIRegimeDetector, RegimeResult
from risk.unified_risk_engine import UnifiedRiskEngine
from execution.order_state_machine import OrderStateMachine
from backtest.tick_simulator import TickLevelMarketSimulator, TickSimulatorConfig


class SignalStrength(Enum):
    VERY_WEAK = "VERY_WEAK"
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    VERY_STRONG = "VERY_STRONG"


class ExecutionQuality(Enum):
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    ACCEPTABLE = "ACCEPTABLE"
    POOR = "POOR"
    REJECTED = "REJECTED"


@dataclass
class FlowSignal:
    """Complete trading signal with quality metadata."""
    symbol: str
    side: str
    size: float
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    strength: SignalStrength
    quality_score: float
    regime: str
    agent_votes: Dict[str, Any]
    risk_metrics: Dict[str, float]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    signal_id: str = ""
    
    def __post_init__(self):
        if not self.signal_id:
            self.signal_id = hashlib.sha256(
                f"{self.symbol}{self.side}{self.timestamp.isoformat()}".encode()
            ).hexdigest()[:16]
    
    def to_dict(self) -> Dict:
        return {
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "side": self.side,
            "size": self.size,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "confidence": self.confidence,
            "strength": self.strength.value,
            "quality_score": self.quality_score,
            "regime": self.regime,
            "agent_votes": self.agent_votes,
            "risk_metrics": self.risk_metrics,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ExecutionResult:
    """Execution result with quality metrics."""
    signal_id: str
    order_id: str
    symbol: str
    side: str
    size: float
    fill_price: float
    slippage: float
    latency_ms: float
    quality: ExecutionQuality
    pnl: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict:
        return {
            "signal_id": self.signal_id,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "size": self.size,
            "fill_price": self.fill_price,
            "slippage": self.slippage,
            "latency_ms": self.latency_ms,
            "quality": self.quality.value,
            "pnl": self.pnl,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class StrategyMetrics:
    """Real-time strategy performance metrics."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    gross_pnl: float = 0.0
    commissions: float = 0.0
    slippage_cost: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    avg_slippage: float = 0.0
    avg_latency_ms: float = 0.0
    quality_score: float = 0.0
    
    def update(self, result: ExecutionResult, commission: float = 0.0):
        self.total_trades += 1
        self.total_pnl += result.pnl - commission
        self.gross_pnl += result.pnl
        self.commissions += commission
        self.slippage_cost += abs(result.slippage) * result.size
        
        if result.pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        if self.total_trades > 0:
            self.win_rate = self.winning_trades / self.total_trades
            self.avg_slippage = self.slippage_cost / self.total_trades
            self.avg_latency_ms = (self.avg_latency_ms * (self.total_trades - 1) + result.latency_ms) / self.total_trades
        
        if self.losing_trades > 0:
            gross_loss = abs(self.gross_pnl - self.total_pnl)
            if gross_loss > 0:
                self.profit_factor = abs(self.total_pnl) / gross_loss
        
        self.quality_score = (
            self.win_rate * 0.3 +
            (1 - min(1, self.avg_slippage * 100)) * 0.3 +
            (1 - min(1, self.avg_latency_ms / 100)) * 0.2 +
            min(1, self.sharpe_ratio / 2.0) * 0.2
        )


class InstitutionalFlowStrategy:
    """
    Institutional-Grade Flow Strategy v4.0
    Integrates all AnatoliaX components for maximum efficiency.
    """

    def __init__(
        self,
        capital: float = 1_000_000,
        max_position_pct: float = 0.02,
        target_sharpe: float = 1.5,
        max_drawdown: float = 0.05,
        enable_tracing: bool = True,
        enable_quality_gates: bool = True,
        consensus_type: ConsensusType = ConsensusType.SUPER_MAJORITY,
    ):
        self.capital = capital
        self.max_position_pct = max_position_pct
        self.target_sharpe = target_sharpe
        self.max_drawdown = max_drawdown
        self.enable_tracing = enable_tracing
        self.enable_quality_gates = enable_quality_gates
        
        self.event_store = EventStore(db_path=":memory:")
        self.event_bus = EventBus(event_store=self.event_store)
        self.messaging = ExactlyOnceMessagingBackbone(db_path=":memory:")
        self.quality_layer = DataQualityLayer()
        
        self.tracing = DistributedTracingPipeline(
            service_name="anatoliax-flow-strategy",
            exporter="memory" if enable_tracing else None,
        )
        
        self.agent_council = AgentCouncil(consensus=consensus_type)
        self.regime_detector = AIRegimeDetector()
        
        self.risk_engine = UnifiedRiskEngine(
            max_daily_dd=max_drawdown,
            max_single_exposure=max_position_pct,
            max_concurrent_positions=10,
        )
        self.risk_engine.update_capital(capital, 0.0)
        
        self.order_state_machine = OrderStateMachine()
        self.tick_simulator = TickLevelMarketSimulator(TickSimulatorConfig(seed=42))
        
        self.metrics = StrategyMetrics()
        self._trade_history: List[ExecutionResult] = []
        self._equity_curve: List[float] = [capital]
        self._quality_cache: Dict[str, DataQualityReport] = {}
        self._regime_cache: Dict[str, str] = {}

    def process_market_data(self, ticks: pd.DataFrame, symbol: str) -> Optional[FlowSignal]:
        """Complete market data processing pipeline."""
        trace_id = None
        
        with self.tracing.tracer.trace("process_market_data", attributes={
            "symbol": symbol,
            "tick_count": len(ticks),
        }) as span:
            trace_id = f"{span.trace_id}-{span.span_id}"
            
            if self.enable_quality_gates:
                quality_report = self._validate_data_quality(ticks, symbol)
                span.set_attribute("data.quality_score", quality_report.quality_score)
                
                if quality_report.level == QualityLevel.CRITICAL:
                    span.set_status(StatusCode.ERROR)
                    return None
            
            regime = self._detect_regime(ticks, symbol)
            span.set_attribute("market.regime", regime)
            
            raw_signal = self._generate_raw_signal(ticks, symbol, regime)
            if not raw_signal:
                return None
            
            council_result = self._get_agent_consensus(raw_signal, ticks)
            
            if council_result["decision"] in [Vote.BLOCK, Vote.WAIT]:
                return None
            
            risk_check = self._validate_risk(raw_signal, council_result, regime)
            
            if not risk_check["passed"]:
                return None
            
            signal = FlowSignal(
                symbol=symbol,
                side=raw_signal["side"],
                size=raw_signal["size"],
                entry_price=raw_signal["entry_price"],
                stop_loss=raw_signal["stop_loss"],
                take_profit=raw_signal["take_profit"],
                confidence=council_result["confidence"],
                strength=self._calculate_signal_strength(council_result),
                quality_score=quality_report.quality_score if self.enable_quality_gates else 0.0,
                regime=regime,
                agent_votes=council_result["votes"],
                risk_metrics=risk_check["metrics"],
            )
            
            self._record_signal_event(signal, trace_id)
            return signal

    def execute(self, signal: FlowSignal) -> ExecutionResult:
        """Execute trading signal with quality monitoring."""
        with self.tracing.tracer.trace("execute_signal", attributes={
            "signal_id": signal.signal_id,
            "symbol": signal.symbol,
        }) as span:
            order_id = f"ORD-{signal.signal_id}"
            self.order_state_machine.create_order(
                order_id=order_id,
                symbol=signal.symbol,
                side=signal.side,
                size=signal.size,
                price=signal.entry_price,
            )
            
            fill_result = self._simulate_execution(signal)
            quality = self._assess_execution_quality(fill_result)
            
            result = ExecutionResult(
                signal_id=signal.signal_id,
                order_id=order_id,
                symbol=signal.symbol,
                side=signal.side,
                size=signal.size,
                fill_price=fill_result["fill_price"],
                slippage=fill_result["slippage"],
                latency_ms=fill_result["latency_ms"],
                quality=quality,
            )
            
            self._update_metrics(result)
            self._record_execution_event(result, signal)
            return result

    def record_feedback(self, result: ExecutionResult, pnl: float):
        """Record trade feedback for learning."""
        with self.tracing.tracer.trace("record_feedback", attributes={
            "pnl": pnl,
            "quality": result.quality.value,
        }):
            result.pnl = pnl
            self._trade_history.append(result)
            
            new_equity = self._equity_curve[-1] + pnl
            self._equity_curve.append(new_equity)
            
            self.risk_engine.update_capital(new_equity, pnl)
            
            self.event_store.append(Event(
                event_type=EventType.PNL,
                payload={
                    "signal_id": result.signal_id,
                    "order_id": result.order_id,
                    "pnl": pnl,
                    "quality": result.quality.value,
                },
            ))
            
            self._update_sharpe_ratio()
            self._update_max_drawdown()

    def get_metrics(self) -> StrategyMetrics:
        return self.metrics

    def get_equity_curve(self) -> List[float]:
        return self._equity_curve

    # Internal methods
    def _validate_data_quality(self, ticks: pd.DataFrame, symbol: str) -> DataQualityReport:
        dataset_id = f"{symbol}_{len(ticks)}"
        
        if dataset_id in self._quality_cache:
            return self._quality_cache[dataset_id]
        
        data = ticks.to_dict('records')
        report = self.quality_layer.validate_dataset(
            data=data,
            data_type=DataType.TICK,
            dataset_id=dataset_id,
            expected_fields=["timestamp", "price", "volume"],
        )
        
        self._quality_cache[dataset_id] = report
        return report

    def _detect_regime(self, ticks: pd.DataFrame, symbol: str) -> str:
        cache_key = f"{symbol}_{len(ticks)}"
        
        if cache_key in self._regime_cache:
            return self._regime_cache[cache_key]
        
        # Prepare data for regime detector (needs 'close' column)
        regime_df = ticks.copy()
        if "close" not in regime_df.columns and "price" in regime_df.columns:
            regime_df["close"] = regime_df["price"]
        
        # Fit and predict using correct API
        self.regime_detector.fit(regime_df)
        regime_result: RegimeResult = self.regime_detector.predict(regime_df)
        
        regime = regime_result.regime
        self._regime_cache[cache_key] = regime
        return regime

    def _generate_raw_signal(self, ticks: pd.DataFrame, symbol: str, regime: str) -> Optional[Dict]:
        if len(ticks) < 20:
            return None
        
        prices = ticks["price"]
        volumes = ticks["volume"]
        
        ma_fast = prices.rolling(10).mean().iloc[-1]
        ma_slow = prices.rolling(20).mean().iloc[-1]
        
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean().iloc[-1]
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1]
        rs = gain / (loss + 1e-6)
        rsi = 100 - (100 / (1 + rs))
        
        vol_ma = volumes.rolling(20).mean().iloc[-1]
        vol_ratio = volumes.iloc[-1] / (vol_ma + 1e-6)
        
        current_price = prices.iloc[-1]
        
        if regime in ["bull", "bullish"]:
            if ma_fast > ma_slow and rsi < 70 and vol_ratio > 1.0:
                side = "BUY"
                confidence = min(95, 50 + (ma_fast - ma_slow) / ma_slow * 1000 + (vol_ratio - 1) * 20)
            else:
                return None
        elif regime in ["bear", "bearish"]:
            if ma_fast < ma_slow and rsi > 30 and vol_ratio > 1.0:
                side = "SELL"
                confidence = min(95, 50 + (ma_slow - ma_fast) / ma_slow * 1000 + (vol_ratio - 1) * 20)
            else:
                return None
        else:
            if rsi < 30:
                side = "BUY"
                confidence = 50 + (50 - rsi)
            elif rsi > 70:
                side = "SELL"
                confidence = 50 + (rsi - 50)
            else:
                return None
        
        position_value = self.capital * self.max_position_pct * (confidence / 100)
        size = position_value / current_price
        
        atr = (prices.rolling(14).max() - prices.rolling(14).min()).iloc[-1]
        stop_loss = current_price - (2 * atr) if side == "BUY" else current_price + (2 * atr)
        take_profit = current_price + (3 * atr) if side == "BUY" else current_price - (3 * atr)
        
        return {
            "side": side,
            "size": size,
            "entry_price": current_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "confidence": confidence,
        }

    def _get_agent_consensus(self, signal: Dict, ticks: pd.DataFrame) -> Dict:
        # Add close column if missing (agent council expects it)
        council_df = ticks.copy()
        if "close" not in council_df.columns and "price" in council_df.columns:
            council_df["close"] = council_df["price"]

        council_signal = {
            "side": signal["side"],
            "confidence": signal["confidence"],
            "setup": "FLOW",
            "entry": signal["entry_price"],
            "sl": signal["stop_loss"],
        }
        
        result = self.agent_council.hold_meeting(
            symbol="FLOW",
            signal=council_signal,
            df=council_df,
        )
        
        return {
            "decision": result.decision,
            "confidence": result.confidence,
            "votes": [v.to_dict() for v in result.votes],
            "consensus_reached": result.consensus_reached,
        }

    def _validate_risk(self, signal: Dict, council_result: Dict, regime: str) -> Dict:
        position_value = signal["size"] * signal["entry_price"]
        position_pct = position_value / self.capital
        
        risk_metrics = {
            "position_pct": position_pct,
            "max_position_pct": self.max_position_pct,
            "regime": regime,
            "council_confidence": council_result["confidence"],
        }
        
        passed = True
        reasons = []
        
        if position_pct > self.max_position_pct:
            passed = False
            reasons.append(f"Position size {position_pct:.2%} > max {self.max_position_pct:.2%}")
        
        if council_result["confidence"] < 60:
            passed = False
            reasons.append(f"Council confidence {council_result['confidence']:.1f}% < 60%")
        
        rr_ratio = abs(signal["take_profit"] - signal["entry_price"]) / abs(signal["entry_price"] - signal["stop_loss"])
        risk_metrics["rr_ratio"] = rr_ratio
        
        if rr_ratio < 1.5:
            passed = False
            reasons.append(f"R:R ratio {rr_ratio:.2f} < 1.5")
        
        return {"passed": passed, "metrics": risk_metrics, "reasons": reasons}

    def _calculate_signal_strength(self, council_result: Dict) -> SignalStrength:
        confidence = council_result["confidence"]
        
        if confidence >= 90:
            return SignalStrength.VERY_STRONG
        elif confidence >= 80:
            return SignalStrength.STRONG
        elif confidence >= 70:
            return SignalStrength.MODERATE
        elif confidence >= 60:
            return SignalStrength.WEAK
        else:
            return SignalStrength.VERY_WEAK

    def _simulate_execution(self, signal: FlowSignal) -> Dict:
        fill = self.tick_simulator.simulate_fill(
            arrival_price=signal.entry_price,
            order_size=signal.size,
            queue_depth=10000,
            volatility=0.02,
            spread=signal.entry_price * 0.001,
            side=signal.side.lower(),
        )
        
        return {
            "fill_price": fill.fill_price,
            "slippage": fill.slippage,
            "latency_ms": fill.latency_ms,
        }

    def _assess_execution_quality(self, fill_result: Dict) -> ExecutionQuality:
        slippage_pct = abs(fill_result["slippage"]) / fill_result["fill_price"]
        
        if slippage_pct < 0.0001:
            return ExecutionQuality.EXCELLENT
        elif slippage_pct < 0.0005:
            return ExecutionQuality.GOOD
        elif slippage_pct < 0.001:
            return ExecutionQuality.ACCEPTABLE
        elif slippage_pct < 0.002:
            return ExecutionQuality.POOR
        else:
            return ExecutionQuality.REJECTED

    def _update_metrics(self, result: ExecutionResult):
        self.metrics.update(result)

    def _update_sharpe_ratio(self):
        if len(self._trade_history) < 10:
            return
        
        returns = [t.pnl for t in self._trade_history[-50:]]
        if len(returns) > 1:
            avg_return = statistics.mean(returns)
            std_return = statistics.stdev(returns)
            if std_return > 0:
                self.metrics.sharpe_ratio = (avg_return / std_return) * np.sqrt(252)

    def _update_max_drawdown(self):
        if len(self._equity_curve) < 2:
            return
        
        peak = self._equity_curve[0]
        max_dd = 0.0
        
        for equity in self._equity_curve:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak
            if dd > max_dd:
                max_dd = dd
        
        self.metrics.max_drawdown = max_dd

    def _record_signal_event(self, signal: FlowSignal, trace_id: str):
        self.event_store.append(Event(
            event_type=EventType.SIGNAL,
            payload=signal.to_dict(),
            correlation_id=trace_id,
        ))
        
        self.messaging.publish(
            topic="signals",
            payload=signal.to_dict(),
            idempotency_key=f"signal-{signal.signal_id}",
            backend="memory",
        )

    def _record_execution_event(self, result: ExecutionResult, signal: FlowSignal):
        self.event_store.append(Event(
            event_type=EventType.FILL,
            payload=result.to_dict(),
            causation_id=signal.signal_id,
        ))
        
        self.messaging.publish(
            topic="executions",
            payload=result.to_dict(),
            idempotency_key=f"exec-{result.order_id}",
            backend="memory",
        )
