"""
risk/adaptive_leverage.py - Adaptive Leverage Engine

Volatility-state modeling, liquidity-depth analysis, nonlinear exposure scaling,
entropy-based risk compression, systemic-risk-aware leverage governance.
"""

import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class LeverageState(Enum):
    MAXIMUM = "maximum"
    REDUCED = "reduced"
    MINIMAL = "minimal"
    ZERO = "zero"


@dataclass
class LeverageDecision:
    symbol: str
    current_leverage: float
    recommended_leverage: float
    state: LeverageState
    volatility_factor: float
    liquidity_factor: float
    entropy_factor: float
    systemic_risk_factor: float
    timestamp: str


class AdaptiveLeverageEngine:
    def __init__(self, max_leverage: float = 3.0):
        self.max_leverage = max_leverage
        self._volatility_history: Dict[str, List[float]] = {}
        self._liquidity_history: Dict[str, List[float]] = {}
        self._leverage_decisions: List[LeverageDecision] = []
        self._current_leverage: Dict[str, float] = {}
    
    def calculate_adaptive_leverage(self, symbol: str,
                                   volatility: float,
                                   liquidity_score: float,
                                   market_entropy: float,
                                   systemic_risk: float) -> LeverageDecision:
        if symbol not in self._volatility_history:
            self._volatility_history[symbol] = []
            self._liquidity_history[symbol] = []
        
        self._volatility_history[symbol].append(volatility)
        self._liquidity_history[symbol].append(liquidity_score)
        
        vol_factor = self._calculate_volatility_factor(symbol, volatility)
        liq_factor = self._calculate_liquidity_factor(liquidity_score)
        entropy_factor = self._calculate_entropy_factor(market_entropy)
        systemic_factor = self._calculate_systemic_factor(systemic_risk)
        
        combined_factor = vol_factor * liq_factor * entropy_factor * systemic_factor
        recommended_leverage = self.max_leverage * combined_factor
        
        if recommended_leverage >= 2.5:
            state = LeverageState.MAXIMUM
        elif recommended_leverage >= 1.5:
            state = LeverageState.REDUCED
        elif recommended_leverage >= 0.5:
            state = LeverageState.MINIMAL
        else:
            state = LeverageState.ZERO
            recommended_leverage = 0.0
        
        current_leverage = self._current_leverage.get(symbol, self.max_leverage)
        
        recommended_leverage = min(recommended_leverage, current_leverage * 1.2)
        recommended_leverage = max(recommended_leverage, current_leverage * 0.5)
        
        self._current_leverage[symbol] = recommended_leverage
        
        decision = LeverageDecision(
            symbol=symbol,
            current_leverage=current_leverage,
            recommended_leverage=recommended_leverage,
            state=state,
            volatility_factor=vol_factor,
            liquidity_factor=liq_factor,
            entropy_factor=entropy_factor,
            systemic_risk_factor=systemic_factor,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        self._leverage_decisions.append(decision)
        return decision
    
    def _calculate_volatility_factor(self, symbol: str,
                                    current_vol: float) -> float:
        if symbol not in self._volatility_history or len(self._volatility_history[symbol]) < 10:
            return 1.0
        
        vol_history = self._volatility_history[symbol][-100:]
        vol_mean = np.mean(vol_history)
        vol_std = np.std(vol_history)
        
        if vol_std == 0:
            return 1.0
        
        vol_zscore = (current_vol - vol_mean) / vol_std
        
        if vol_zscore > 2.0:
            return 0.3
        elif vol_zscore > 1.0:
            return 0.6
        elif vol_zscore < -1.0:
            return 1.0
        else:
            return 0.8
    
    def _calculate_liquidity_factor(self, liquidity_score: float) -> float:
        if liquidity_score >= 0.8:
            return 1.0
        elif liquidity_score >= 0.6:
            return 0.7
        elif liquidity_score >= 0.4:
            return 0.4
        else:
            return 0.2
    
    def _calculate_entropy_factor(self, entropy: float) -> float:
        if entropy < 0.3:
            return 1.0
        elif entropy < 0.5:
            return 0.7
        elif entropy < 0.7:
            return 0.4
        else:
            return 0.2
    
    def _calculate_systemic_factor(self, systemic_risk: float) -> float:
        if systemic_risk < 0.2:
            return 1.0
        elif systemic_risk < 0.4:
            return 0.7
        elif systemic_risk < 0.6:
            return 0.4
        else:
            return 0.1
    
    def get_leverage_report(self, symbol: str) -> Dict[str, Any]:
        decisions = [d for d in self._leverage_decisions if d.symbol == symbol]
        
        if not decisions:
            return {'error': 'No leverage decisions'}
        
        latest = decisions[-1]
        
        return {
            'symbol': symbol,
            'current_leverage': latest.current_leverage,
            'recommended_leverage': latest.recommended_leverage,
            'state': latest.state.value,
            'volatility_factor': latest.volatility_factor,
            'liquidity_factor': latest.liquidity_factor,
            'entropy_factor': latest.entropy_factor,
            'systemic_risk_factor': latest.systemic_risk_factor,
            'max_allowed': self.max_leverage,
        }
    
    def get_global_leverage_report(self) -> Dict[str, Any]:
        return {
            'max_leverage': self.max_leverage,
            'symbols_tracked': len(self._current_leverage),
            'current_leverages': self._current_leverage,
            'total_decisions': len(self._leverage_decisions),
        }


_adaptive_leverage: Optional[AdaptiveLeverageEngine] = None

def get_adaptive_leverage_engine(max_leverage: float = 3.0) -> AdaptiveLeverageEngine:
    global _adaptive_leverage
    if _adaptive_leverage is None:
        _adaptive_leverage = AdaptiveLeverageEngine(max_leverage=max_leverage)
    return _adaptive_leverage
