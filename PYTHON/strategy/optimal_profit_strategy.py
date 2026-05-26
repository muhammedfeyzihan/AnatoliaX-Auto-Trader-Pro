"""
PYTHON/strategy/optimal_profit_strategy.py — Optimal Profit Master Strategy

Bu strateji tum 30 kurumsal ozelligi bir araya getirir:
- Regime-based strategy selection
- Meta-learning ile surekli gelisim
- Capital preservation oncelikli
- En hizli kazanclı yol optimizasyonu
- Risk-minimized trading

Features:
- Tum 30 institutional feature entegrasyonu
- Self-improving via meta-learning
- Regime-adaptive (trend/range/high-volatility)
- Knowledge base integration
- Real-time risk adjustment
"""
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json


class MarketRegime(Enum):
    """Piyasa rejimleri."""
    TREND_BULL = "trend_bull"
    TREND_BEAR = "trend_bear"
    RANGE = "range"
    HIGH_VOLATILITY = "high_volatility"
    CRISIS = "crisis"
    LOW_LIQUIDITY = "low_liquidity"


class StrategyMode(Enum):
    """Strateji modlari."""
    AGGRESSIVE = "aggressive"      # Yuksek risk, yuksek getiri
    BALANCED = "balanced"          # Orta risk, orta getiri
    CONSERVATIVE = "conservative"  # Dusuk risk, dusuk getiri
    PRESERVATION = "preservation"  # Sermaye koruma (kill-switch yakin)


@dataclass
class StrategyConfig:
    """Strateji yapilandirmasi."""
    mode: StrategyMode = StrategyMode.BALANCED
    max_daily_loss_pct: float = 2.0
    target_daily_profit_pct: float = 1.0
    max_position_size_pct: float = 10.0
    max_correlation: float = 0.7
    min_sharpe_ratio: float = 1.5
    max_drawdown_pct: float = 5.0
    enable_meta_learning: bool = True
    enable_knowledge_integration: bool = True
    enable_explainability: bool = True


@dataclass
class TradeSignal:
    """Trade sinyali."""
    symbol: str
    direction: str  # "LONG" or "SHORT"
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size_pct: float
    confidence: float
    regime: MarketRegime
    reasoning: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expiry: Optional[datetime] = None


class OptimalProfitStrategy:
    """
    Optimal Profit Master Strategy.
    
    Tum 30 kurumsal ozelligi bir araya getirerek
    maksimum karlilik ve minimum risk hedefler.
    
    Integrations:
    1. Exchange Failure Simulation
    2. Nanosecond Tick Replay
    3. Adaptive Portfolio Hedging
    4. AI Meta-Learning
    5. Liquidity Intelligence
    6. Regime Detection AI
    7. Macro-Event Intelligence
    8. Chaos Engineering
    9. Self-Healing Infrastructure
    10. Cryptographic Audit
    11. Position Sizing Pro
    12. Crisis Correlation
    13. Synthetic Market Generator
    14. Explainable AI
    15. Multi-Agent Consensus
    16. Exchange Defense
    17. Military Secret Management
    18. Distributed Observability
    19. Institutional Execution
    20. Slippage & TCA
    21. Capital Preservation
    22. Distributed AI Memory
    23. Institutional Backtest
    24. Options Risk
    25. AI Execution Surveillance
    26. Distributed Data Validation
    27. Adaptive Leverage
    28. Institutional Portfolio
    29. Strategy Sandboxing
    30. AI Governance
    """
    
    def __init__(self, config: StrategyConfig = None):
        self.config = config or StrategyConfig()
        self._regime = MarketRegime.RANGE
        self._mode = self.config.mode
        self._performance_history: List[Dict] = []
        self._active_trades: List[TradeSignal] = []
        self._meta_learning_state: Dict[str, Any] = {}
        self._knowledge_base = None
        self._initialized = False
        
        # Feature modules (wired externally)
        self._modules: Dict[str, Any] = {}
    
    def initialize(self, modules: Dict[str, Any], knowledge_base=None) -> None:
        """
        Tum 30 modulu bagla.
        
        Args:
            modules: Dict of module_name -> module_instance
            knowledge_base: KnowledgeBase instance
        """
        self._modules = modules
        self._knowledge_base = knowledge_base
        self._initialized = True
        
        # Module validation
        required_modules = [
            'regime_detector', 'meta_learner', 'risk_engine',
            'execution_engine', 'liquidity_intelligence',
            'macro_intelligence', 'capital_preservation',
            'position_sizing', 'portfolio_optimizer'
        ]
        for mod in required_modules:
            if mod not in modules:
                raise ValueError(f"Required module missing: {mod}")
    
    def _detect_regime(self, market_data: Dict[str, Any]) -> MarketRegime:
        """
        Piyasa rejimini tespit et.
        
        Uses: Regime Detection AI (Feature #6)
        """
        regime_detector = self._modules.get('regime_detector')
        if regime_detector and hasattr(regime_detector, 'detect'):
            regime_str = regime_detector.detect(market_data)
            try:
                return MarketRegime(regime_str)
            except ValueError:
                pass
        
        # Fallback: basit rejim tespiti
        volatility = market_data.get('volatility', 0)
        trend_strength = market_data.get('trend_strength', 0)
        
        if volatility > 0.03:
            return MarketRegime.HIGH_VOLATILITY
        elif trend_strength > 0.7:
            direction = market_data.get('trend_direction', 0)
            return MarketRegime.TREND_BULL if direction > 0 else MarketRegime.TREND_BEAR
        elif volatility < 0.01:
            return MarketRegime.LOW_LIQUIDITY
        else:
            return MarketRegime.RANGE
    
    def _select_strategy_mode(self, regime: MarketRegime) -> StrategyMode:
        """
        Rejime gore strateji modu sec.
        
        Rules:
        - Crisis/High Volatility -> Preservation
        - Trend -> Aggressive
        - Range -> Balanced
        - Low Liquidity -> Conservative
        """
        if regime in [MarketRegime.CRISIS, MarketRegime.HIGH_VOLATILITY]:
            return StrategyMode.PRESERVATION
        elif regime in [MarketRegime.TREND_BULL, MarketRegime.TREND_BEAR]:
            return StrategyMode.AGGRESSIVE
        elif regime == MarketRegime.RANGE:
            return StrategyMode.BALANCED
        else:
            return StrategyMode.CONSERVATIVE
    
    def _calculate_position_size(self, signal: Dict[str, Any], 
                                  regime: MarketRegime) -> float:
        """
        Pozisyon boyutu hesapla.
        
        Uses: Position Sizing Pro (Feature #11)
        - Fractional Kelly
        - Entropy-weighted
        - Volatility targeting
        - Drawdown-aware
        """
        position_sizing = self._modules.get('position_sizing')
        if position_sizing and hasattr(position_sizing, 'calculate'):
            return position_sizing.calculate(
                signal=signal,
                regime=regime.value,
                mode=self._mode.value
            )
        
        # Fallback: basit Kelly
        win_rate = signal.get('win_rate', 0.55)
        reward_ratio = signal.get('reward_ratio', 1.5)
        
        kelly = (win_rate * (reward_ratio + 1) - 1) / reward_ratio
        kelly = max(0, min(kelly, 0.25))  # Cap at 25%
        
        # Mode adjustment
        mode_multipliers = {
            StrategyMode.AGGRESSIVE: 1.0,
            StrategyMode.BALANCED: 0.7,
            StrategyMode.CONSERVATIVE: 0.5,
            StrategyMode.PRESERVATION: 0.25
        }
        
        return kelly * mode_multipliers[self._mode]
    
    def _apply_risk_checks(self, signal: TradeSignal) -> Tuple[bool, str]:
        """
        Risk kontrolleri uygula.
        
        Uses:
        - Capital Preservation (Feature #21)
        - Crisis Correlation (Feature #12)
        - Adaptive Leverage (Feature #27)
        """
        # Capital preservation check
        capital_preservation = self._modules.get('capital_preservation')
        if capital_preservation and hasattr(capital_preservation, 'should_allow_trade'):
            allowed, reason = capital_preservation.should_allow_trade(
                signal=signal,
                daily_pnl=self._get_daily_pnl(),
                drawdown=self._get_current_drawdown()
            )
            if not allowed:
                return False, reason
        
        # Correlation check
        crisis_corr = self._modules.get('crisis_correlation')
        if crisis_corr and hasattr(crisis_corr, 'check_correlation'):
            if not crisis_corr.check_correlation(signal.symbol):
                return False, "High correlation risk detected"
        
        # Leverage check
        adaptive_leverage = self._modules.get('adaptive_leverage')
        if adaptive_leverage and hasattr(adaptive_leverage, 'get_max_leverage'):
            max_lev = adaptive_leverage.get_max_leverage()
            if signal.position_size_pct > max_lev:
                return False, f"Leverage exceeds max {max_lev*100}%"
        
        return True, "Risk checks passed"
    
    def _get_knowledge_context(self, symbol: str) -> Dict[str, Any]:
        """
        Knowledge base'den baglam al.
        
        Uses: Knowledge Base Integration
        """
        if not self._knowledge_base:
            return {}
        
        return self._knowledge_base.get_knowledge_for_decision(
            symbol=symbol,
            context={'regime': self._regime.value}
        )
    
    def _generate_signal(self, symbol: str, market_data: Dict[str, Any]) -> Optional[TradeSignal]:
        """
        Trade sinyali uret.
        
        Uses:
        - Multi-Agent Consensus (Feature #15)
        - Liquidity Intelligence (Feature #5)
        - Macro-Event Intelligence (Feature #7)
        - Explainable AI (Feature #14)
        """
        # Get agent consensus
        agent_council = self._modules.get('agent_council')
        if not agent_council:
            return None
        
        # Get knowledge context
        knowledge = self._get_knowledge_context(symbol)
        
        # Build analysis context
        context = {
            'market_data': market_data,
            'regime': self._regime.value,
            'knowledge': knowledge,
            'mode': self._mode.value
        }
        
        # Get consensus decision
        if hasattr(agent_council, 'get_consensus'):
            consensus = agent_council.get_consensus(symbol, context)
        else:
            return None
        
        if not consensus.get('approved', False):
            return None
        
        # Calculate levels
        current_price = market_data.get('price', 0)
        volatility = market_data.get('volatility', 0.02)
        
        direction = consensus.get('direction', 'LONG')
        if direction == 'LONG':
            stop_loss = current_price * (1 - volatility * 2)
            take_profit = current_price * (1 + volatility * 3)
        else:
            stop_loss = current_price * (1 + volatility * 2)
            take_profit = current_price * (1 - volatility * 3)
        
        # Calculate position size
        signal_data = {
            'win_rate': consensus.get('confidence', 0.6),
            'reward_ratio': 1.5
        }
        position_size = self._calculate_position_size(signal_data, self._regime)
        
        # Build reasoning (Explainable AI)
        reasoning = {
            'agent_votes': consensus.get('votes', {}),
            'regime': self._regime.value,
            'mode': self._mode.value,
            'knowledge_used': bool(knowledge),
            'confidence': consensus.get('confidence', 0),
            'features': consensus.get('features', {})
        }
        
        return TradeSignal(
            symbol=symbol,
            direction=direction,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size_pct=position_size,
            confidence=consensus.get('confidence', 0),
            regime=self._regime,
            reasoning=reasoning
        )
    
    def _get_daily_pnl(self) -> float:
        """Gunluk PnL hesapla."""
        if not self._performance_history:
            return 0.0
        
        today = datetime.now(timezone.utc).date()
        daily_pnl = sum(
            trade.get('pnl', 0) for trade in self._performance_history
            if datetime.fromisoformat(trade['timestamp']).date() == today
        )
        return daily_pnl
    
    def _get_current_drawdown(self) -> float:
        """Mevcut drawdown hesapla."""
        if not self._performance_history:
            return 0.0
        
        cumulative = 0
        max_cumulative = 0
        max_drawdown = 0
        
        for trade in sorted(self._performance_history, key=lambda x: x['timestamp']):
            cumulative += trade.get('pnl', 0)
            max_cumulative = max(max_cumulative, cumulative)
            drawdown = (max_cumulative - cumulative) / max_cumulative if max_cumulative > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown
    
    def analyze(self, symbol: str, market_data: Dict[str, Any]) -> Optional[TradeSignal]:
        """
        Ana analiz fonksiyonu.
        
        Args:
            symbol: Trade edilecek sembol
            market_data: Piyasa verileri (price, volatility, volume, etc.)
        
        Returns:
            TradeSignal or None (no trade)
        """
        if not self._initialized:
            raise RuntimeError("Strategy not initialized. Call initialize() first.")
        
        # Step 1: Detect regime
        self._regime = self._detect_regime(market_data)
        
        # Step 2: Select strategy mode
        self._mode = self._select_strategy_mode(self._regime)
        
        # Step 3: Check macro events
        macro_intel = self._modules.get('macro_intelligence')
        if macro_intel and hasattr(macro_intel, 'is_safe_to_trade'):
            if not macro_intel.is_safe_to_trade():
                return None  # Major event pending, no trading
        
        # Step 4: Check liquidity
        liq_intel = self._modules.get('liquidity_intelligence')
        if liq_intel and hasattr(liq_intel, 'check_liquidity'):
            if not liq_intel.check_liquidity(symbol):
                return None  # Low liquidity, no trading
        
        # Step 5: Generate signal
        signal = self._generate_signal(symbol, market_data)
        if not signal:
            return None
        
        # Step 6: Risk checks
        allowed, reason = self._apply_risk_checks(signal)
        if not allowed:
            return None
        
        # Step 7: Record signal
        self._active_trades.append(signal)
        
        return signal
    
    def record_trade_result(self, symbol: str, pnl: float, 
                           reasoning: str, features: Dict[str, Any]) -> None:
        """
        Trade sonucunu kaydet ve ogren.
        
        Uses:
        - Meta-Learning (Feature #4)
        - Knowledge Base
        """
        result = {
            'symbol': symbol,
            'pnl': pnl,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'reasoning': reasoning,
            'features': features,
            'regime': self._regime.value,
            'mode': self._mode.value
        }
        self._performance_history.append(result)
        
        # Add to knowledge base
        if self._knowledge_base:
            self._knowledge_base.add_trade_learning(
                symbol=symbol,
                outcome='profit' if pnl > 0 else 'loss',
                pnl=pnl,
                reasoning=reasoning,
                features=features
            )
        
        # Meta-learning update
        if self.config.enable_meta_learning:
            meta_learner = self._modules.get('meta_learner')
            if meta_learner and hasattr(meta_learner, 'update'):
                meta_learner.update(result)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Performans istatistikleri al.
        
        Returns:
            Dict with sharpe, drawdown, win_rate, total_pnl, etc.
        """
        if not self._performance_history:
            return {
                'total_trades': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0
            }
        
        pnls = [t['pnl'] for t in self._performance_history]
        wins = sum(1 for p in pnls if p > 0)
        
        sharpe = np.mean(pnls) / np.std(pnls) if len(pnls) > 1 and np.std(pnls) > 0 else 0
        
        return {
            'total_trades': len(self._performance_history),
            'sharpe_ratio': sharpe,
            'max_drawdown': self._get_current_drawdown(),
            'win_rate': wins / len(pnls) if pnls else 0,
            'total_pnl': sum(pnls),
            'avg_pnl': np.mean(pnls) if pnls else 0,
            'profit_factor': sum(p for p in pnls if p > 0) / abs(sum(p for p in pnls if p < 0)) if any(p < 0 for p in pnls) else float('inf')
        }
    
    def get_explanation(self, signal: TradeSignal) -> Dict[str, Any]:
        """
        Trade aciklamasi uret (Explainable AI).
        
        Uses: Explainable AI (Feature #14)
        """
        xai_module = self._modules.get('explainable_ai')
        if xai_module and hasattr(xai_module, 'explain'):
            return xai_module.explain(signal)
        
        # Fallback: basit aciklama
        return {
            'symbol': signal.symbol,
            'direction': signal.direction,
            'confidence': signal.confidence,
            'regime': signal.regime.value,
            'reasoning': signal.reasoning,
            'risk_reward': (signal.take_profit - signal.entry_price) / (signal.entry_price - signal.stop_loss)
        }
    
    def should_exit_trade(self, symbol: str, current_price: float) -> Optional[str]:
        """
        Trade'den cikis zamani mi kontrol et.
        
        Returns:
            "STOP_LOSS", "TAKE_PROFIT", or None
        """
        for trade in self._active_trades:
            if trade.symbol == symbol:
                if trade.direction == 'LONG':
                    if current_price <= trade.stop_loss:
                        return 'STOP_LOSS'
                    elif current_price >= trade.take_profit:
                        return 'TAKE_PROFIT'
                else:
                    if current_price >= trade.stop_loss:
                        return 'STOP_LOSS'
                    elif current_price <= trade.take_profit:
                        return 'TAKE_PROFIT'
        return None
    
    def reset_daily(self) -> None:
        """Gunluk sifirlama."""
        self._active_trades.clear()
        # Keep performance history for learning


# Factory function
def create_optimal_strategy(config: StrategyConfig = None) -> OptimalProfitStrategy:
    """Optimal strateji factory."""
    return OptimalProfitStrategy(config=config)

