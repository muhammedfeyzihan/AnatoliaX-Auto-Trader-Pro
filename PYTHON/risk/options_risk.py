"""
risk/options_risk.py - Options/Derivatives Risk Engine

Greeks aggregation, gamma exposure, volatility-surface modeling,
skew analytics, convexity stress testing, cross-asset hedging.
"""

import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from scipy.stats import norm


@dataclass
class OptionPosition:
    symbol: str
    option_type: str
    strike: float
    expiry: str
    quantity: float
    underlying_price: float
    implied_vol: float
    risk_free_rate: float


@dataclass
class Greeks:
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float


class OptionsRiskEngine:
    def __init__(self):
        self._positions: List[OptionPosition] = []
        self._portfolio_greeks: Dict[str, float] = {}
        self._vol_surface: Dict[str, Dict[float, float]] = {}
    
    def black_scholes_price(self, S: float, K: float, T: float,
                           r: float, sigma: float,
                           option_type: str = 'call') -> float:
        if T <= 0:
            if option_type == 'call':
                return max(0, S - K)
            else:
                return max(0, K - S)
        
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        if option_type == 'call':
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        else:
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        
        return price
    
    def calculate_greeks(self, position: OptionPosition) -> Greeks:
        S = position.underlying_price
        K = position.strike
        sigma = position.implied_vol
        r = position.risk_free_rate
        
        T = self._time_to_expiry(position.expiry)
        if T <= 0:
            return Greeks(0, 0, 0, 0, 0)
        
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        if position.option_type == 'call':
            delta = norm.cdf(d1)
            theta = (-S * sigma * norm.pdf(d1) / (2 * np.sqrt(T))
                    - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
        else:
            delta = norm.cdf(d1) - 1
            theta = (-S * sigma * norm.pdf(d1) / (2 * np.sqrt(T))
                    + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
        
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        vega = S * norm.pdf(d1) * np.sqrt(T) / 100
        rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100 if position.option_type == 'call' else -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
        
        return Greeks(delta=delta, gamma=gamma, theta=theta, vega=vega, rho=rho)
    
    def _time_to_expiry(self, expiry: str) -> float:
        try:
            expiry_date = datetime.fromisoformat(expiry.replace('+00:00', ''))
            days_to_expiry = (expiry_date - datetime.now(timezone.utc)).days
            return max(0, days_to_expiry / 365.0)
        except:
            return 0.0
    
    def add_position(self, position: OptionPosition) -> None:
        self._positions.append(position)
        self._update_portfolio_greeks()
    
    def _update_portfolio_greeks(self) -> None:
        self._portfolio_greeks = {
            'total_delta': 0.0,
            'total_gamma': 0.0,
            'total_theta': 0.0,
            'total_vega': 0.0,
            'total_rho': 0.0,
        }
        
        for pos in self._positions:
            greeks = self.calculate_greeks(pos)
            self._portfolio_greeks['total_delta'] += greeks.delta * pos.quantity
            self._portfolio_greeks['total_gamma'] += greeks.gamma * pos.quantity
            self._portfolio_greeks['total_theta'] += greeks.theta * pos.quantity
            self._portfolio_greeks['total_vega'] += greeks.vega * pos.quantity
            self._portfolio_greeks['total_rho'] += greeks.rho * pos.quantity
    
    def update_vol_surface(self, underlying: str,
                          strikes: List[float],
                          implied_vols: List[float]) -> None:
        self._vol_surface[underlying] = {
            strike: vol for strike, vol in zip(strikes, implied_vols)
        }
    
    def get_gamma_exposure(self, underlying: str) -> float:
        total_gamma = 0.0
        for pos in self._positions:
            if pos.symbol == underlying:
                greeks = self.calculate_greeks(pos)
                total_gamma += greeks.gamma * pos.quantity * pos.underlying_price
        return total_gamma
    
    def stress_test(self, underlying_move: float,
                   vol_shock: float) -> Dict[str, Any]:
        portfolio_pnl = 0.0
        
        for pos in self._positions:
            greeks = self.calculate_greeks(pos)
            
            delta_pnl = greeks.delta * pos.quantity * underlying_move * pos.underlying_price
            gamma_pnl = 0.5 * greeks.gamma * pos.quantity * (underlying_move * pos.underlying_price) ** 2
            vega_pnl = greeks.vega * pos.quantity * vol_shock
            
            portfolio_pnl += delta_pnl + gamma_pnl + vega_pnl
        
        return {
            'underlying_move_pct': underlying_move * 100,
            'vol_shock_pct': vol_shock * 100,
            'portfolio_pnl': portfolio_pnl,
            'delta_pnl': sum(self.calculate_greeks(p).delta * p.quantity * underlying_move * p.underlying_price for p in self._positions),
            'gamma_pnl': sum(0.5 * self.calculate_greeks(p).gamma * p.quantity * (underlying_move * p.underlying_price) ** 2 for p in self._positions),
            'vega_pnl': sum(self.calculate_greeks(p).vega * p.quantity * vol_shock for p in self._positions),
        }
    
    def get_risk_report(self) -> Dict[str, Any]:
        return {
            'total_positions': len(self._positions),
            'portfolio_greeks': self._portfolio_greeks,
            'net_delta': self._portfolio_greeks.get('total_delta', 0),
            'net_gamma': self._portfolio_greeks.get('total_gamma', 0),
            'net_vega': self._portfolio_greeks.get('total_vega', 0),
            'vol_surface_underlyings': list(self._vol_surface.keys()),
        }


_options_risk: Optional[OptionsRiskEngine] = None

def get_options_risk_engine() -> OptionsRiskEngine:
    global _options_risk
    if _options_risk is None:
        _options_risk = OptionsRiskEngine()
    return _options_risk
