"""
risk/position_sizing_pro.py - Institutional Position Sizing Engine

Fractional Kelly adaptation, entropy-weighted sizing, convex leverage scaling,
volatility targeting, drawdown-aware sizing, probabilistic capital preservation.
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class PositionSize:
    symbol: str
    recommended_size: float
    kelly_fraction: float
    entropy_weight: float
    volatility_adjustment: float
    drawdown_adjustment: float
    final_size: float
    risk_limit_compliance: bool
    timestamp: str


class PositionSizingEnginePro:
    def __init__(self, initial_capital: float = 1_000_000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self._trade_history: Dict[str, List[Dict]] = {}
        self._performance_metrics: Dict[str, Dict] = {}
        self._max_drawdown = 0.0
        self._peak_capital = initial_capital
    
    def calculate_kelly_fraction(self, symbol: str,
                                win_rate: float,
                                avg_win: float,
                                avg_loss: float) -> float:
        if avg_loss == 0:
            return 0.0
        
        win_loss_ratio = avg_win / abs(avg_loss)
        kelly = win_rate - (1 - win_rate) / win_loss_ratio
        
        fractional_kelly = kelly * 0.25
        return max(0.0, min(0.25, fractional_kelly))
    
    def calculate_entropy_weight(self, symbol: str,
                                returns: List[float]) -> float:
        if len(returns) < 10:
            return 1.0
        
        returns_array = np.array(returns)
        mean_return = np.mean(returns_array)
        std_return = np.std(returns_array)
        
        if std_return == 0:
            return 1.0
        
        entropy = -np.sum(returns_array * np.log(np.abs(returns_array) + 1e-6)) / len(returns_array)
        entropy_weight = 1.0 / (1.0 + np.exp(-entropy / 10))
        
        return max(0.1, min(1.0, entropy_weight))
    
    def calculate_volatility_adjustment(self, symbol: str,
                                       current_vol: float,
                                       target_vol: float = 0.15) -> float:
        if current_vol == 0:
            return 1.0
        
        vol_ratio = target_vol / current_vol
        return max(0.1, min(2.0, vol_ratio))
    
    def calculate_drawdown_adjustment(self) -> float:
        current_dd = (self._peak_capital - self.current_capital) / self._peak_capital
        
        if current_dd > 0.10:
            return 0.25
        elif current_dd > 0.05:
            return 0.5
        elif current_dd > 0.02:
            return 0.75
        else:
            return 1.0
    
    def calculate_position_size(self, symbol: str,
                               signal_confidence: float,
                               current_price: float,
                               volatility: float,
                               correlation_matrix: Optional[Dict] = None) -> PositionSize:
        if symbol not in self._trade_history:
            self._trade_history[symbol] = []
        
        history = self._trade_history[symbol]
        
        if len(history) >= 10:
            wins = [t for t in history if t['pnl'] > 0]
            losses = [t for t in history if t['pnl'] <= 0]
            
            win_rate = len(wins) / len(history)
            avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0.0
            avg_loss = np.mean([t['pnl'] for t in losses]) if losses else -1.0
            
            returns = [t['pnl'] for t in history]
        else:
            win_rate = 0.5
            avg_win = 100.0
            avg_loss = -50.0
            returns = [0.0] * 10
        
        kelly_fraction = self.calculate_kelly_fraction(symbol, win_rate, avg_win, avg_loss)
        entropy_weight = self.calculate_entropy_weight(symbol, returns)
        vol_adjustment = self.calculate_volatility_adjustment(symbol, volatility)
        dd_adjustment = self.calculate_drawdown_adjustment()
        
        base_size = self.current_capital * kelly_fraction * signal_confidence
        adjusted_size = base_size * entropy_weight * vol_adjustment * dd_adjustment
        
        position_value = adjusted_size * current_price
        risk_limit = self.current_capital * 0.02
        risk_compliant = position_value <= risk_limit
        
        size = PositionSize(
            symbol=symbol,
            recommended_size=adjusted_size,
            kelly_fraction=kelly_fraction,
            entropy_weight=entropy_weight,
            volatility_adjustment=vol_adjustment,
            drawdown_adjustment=dd_adjustment,
            final_size=min(adjusted_size, risk_limit / current_price),
            risk_limit_compliance=risk_compliant,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        return size
    
    def record_trade(self, symbol: str, pnl: float) -> None:
        if symbol not in self._trade_history:
            self._trade_history[symbol] = []
        
        self._trade_history[symbol].append({
            'pnl': pnl,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
        
        self.current_capital += pnl
        
        if self.current_capital > self._peak_capital:
            self._peak_capital = self.current_capital
        
        current_dd = (self._peak_capital - self.current_capital) / self._peak_capital
        if current_dd > self._max_drawdown:
            self._max_drawdown = current_dd
    
    def update_capital(self, new_capital: float) -> None:
        self.current_capital = new_capital
        if new_capital > self._peak_capital:
            self._peak_capital = new_capital
    
    def get_sizing_report(self, symbol: str) -> Dict[str, Any]:
        if symbol not in self._trade_history:
            return {'error': 'No trade history'}
        
        history = self._trade_history[symbol]
        
        if len(history) == 0:
            return {'error': 'Empty history'}
        
        wins = [t for t in history if t['pnl'] > 0]
        losses = [t for t in history if t['pnl'] <= 0]
        
        return {
            'symbol': symbol,
            'total_trades': len(history),
            'win_rate': len(wins) / len(history) if history else 0,
            'avg_win': np.mean([t['pnl'] for t in wins]) if wins else 0,
            'avg_loss': np.mean([t['pnl'] for t in losses]) if losses else 0,
            'profit_factor': abs(sum(t['pnl'] for t in wins) / sum(t['pnl'] for t in losses)) if losses and sum(t['pnl'] for t in losses) != 0 else float('inf'),
            'current_capital': self.current_capital,
            'max_drawdown': self._max_drawdown,
        }
    
    def get_global_sizing_report(self) -> Dict[str, Any]:
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'peak_capital': self._peak_capital,
            'max_drawdown': self._max_drawdown,
            'symbols_tracked': len(self._trade_history),
            'total_trades': sum(len(h) for h in self._trade_history.values()),
        }


_position_sizing_pro: Optional[PositionSizingEnginePro] = None

def get_position_sizing_pro(initial_capital: float = 1_000_000) -> PositionSizingEnginePro:
    global _position_sizing_pro
    if _position_sizing_pro is None:
        _position_sizing_pro = PositionSizingEnginePro(initial_capital=initial_capital)
    return _position_sizing_pro
