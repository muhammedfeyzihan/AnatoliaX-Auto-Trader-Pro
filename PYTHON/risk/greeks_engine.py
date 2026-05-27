"""
PYTHON/risk/greeks_engine.py — Real-Time Greeks Engine for Options

CRITICAL COMPONENT #9 from Missing Components PDF

Features:
- Delta, Gamma, Theta, Vega, Rho calculation
- Portfolio-level Greeks aggregation
- Real-time risk exposure monitoring
- Greeks-based hedging recommendations
- Options chain integration

Problem Statement: "What are my options risks?"
Without this: System cannot trade options safely
"""
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from scipy.stats import norm


class OptionType(Enum):
    CALL = "call"
    PUT = "put"


@dataclass
class OptionPosition:
    """Single option position."""
    symbol: str
    option_type: OptionType
    strike: float
    expiry: datetime
    underlying_price: float
    quantity: int
    entry_price: float
    current_price: float
    implied_volatility: float
    risk_free_rate: float = 0.05


@dataclass
class Greeks:
    """Option Greeks."""
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    rho: float = 0.0


@dataclass
class PortfolioGreeks:
    """Portfolio-level Greeks."""
    total_delta: float
    total_gamma: float
    total_theta: float
    total_vega: float
    total_rho: float
    delta_equivalent: float  # Delta * underlying_price * quantity
    gamma_dollar: float  # Gamma * underlying_price^2 * quantity / 100
    theta_daily: float  # Theta * underlying_price * quantity / 365
    vega_1pct: float  # Vega * underlying_price * quantity / 100


class GreeksEngine:
    """
    Real-Time Greeks Engine for Options.
    
    Calculates Black-Scholes Greeks for individual options
    and aggregates at portfolio level.
    """
    
    def __init__(self):
        self._positions: Dict[str, OptionPosition] = {}
        self._underlying_prices: Dict[str, float] = {}
    
    def _black_scholes_price(self, S: float, K: float, T: float, 
                             r: float, sigma: float, option_type: OptionType) -> float:
        """Calculate Black-Scholes option price."""
        if T <= 0:
            # Expired option
            if option_type == OptionType.CALL:
                return max(0, S - K)
            else:
                return max(0, K - S)
        
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        if option_type == OptionType.CALL:
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        else:
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        
        return price
    
    def _calculate_greeks(self, position: OptionPosition) -> Greeks:
        """Calculate Greeks for single option position."""
        S = position.underlying_price
        K = position.strike
        r = position.risk_free_rate
        sigma = position.implied_volatility
        
        # Time to expiry in years
        T = (position.expiry - datetime.now(timezone.utc)).total_seconds() / (365 * 24 * 3600)
        T = max(T, 0.001)  # Minimum 1 day to avoid division by zero
        
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        # Delta
        if position.option_type == OptionType.CALL:
            delta = norm.cdf(d1)
        else:
            delta = norm.cdf(d1) - 1
        
        # Gamma (same for call and put)
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        
        # Theta (daily)
        if position.option_type == OptionType.CALL:
            theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
                    - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
        else:
            theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
                    + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
        
        # Vega (per 1% change in IV)
        vega = S * norm.pdf(d1) * np.sqrt(T) / 100
        
        # Rho (per 1% change in rate)
        if position.option_type == OptionType.CALL:
            rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100
        else:
            rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
        
        return Greeks(delta=delta, gamma=gamma, theta=theta, vega=vega, rho=rho)
    
    def add_position(self, position: OptionPosition) -> None:
        """Add option position."""
        self._positions[position.symbol] = position
    
    def remove_position(self, symbol: str) -> None:
        """Remove option position."""
        if symbol in self._positions:
            del self._positions[symbol]
    
    def update_underlying_price(self, symbol: str, price: float) -> None:
        """Update underlying price."""
        self._underlying_prices[symbol] = price
        
        # Update positions for this underlying
        for pos in self._positions.values():
            if pos.symbol.startswith(symbol):
                pos.underlying_price = price
    
    def get_position_greeks(self, symbol: str) -> Optional[Greeks]:
        """Get Greeks for single position."""
        position = self._positions.get(symbol)
        if not position:
            return None
        
        # Update underlying price if available
        underlying = symbol.split('.')[0]  # Remove option suffix
        if underlying in self._underlying_prices:
            position.underlying_price = self._underlying_prices[underlying]
        
        return self._calculate_greeks(position)
    
    def get_portfolio_greeks(self) -> PortfolioGreeks:
        """Calculate portfolio-level Greeks."""
        total_delta = 0.0
        total_gamma = 0.0
        total_theta = 0.0
        total_vega = 0.0
        total_rho = 0.0
        delta_equivalent = 0.0
        gamma_dollar = 0.0
        theta_daily = 0.0
        vega_1pct = 0.0
        
        for symbol, position in self._positions.items():
            greeks = self._calculate_greeks(position)
            qty = position.quantity
            
            total_delta += greeks.delta * qty
            total_gamma += greeks.gamma * qty
            total_theta += greeks.theta * qty
            total_vega += greeks.vega * qty
            total_rho += greeks.rho * qty
            
            # Dollar Greeks
            delta_equivalent += greeks.delta * position.underlying_price * qty
            gamma_dollar += greeks.gamma * position.underlying_price ** 2 * qty / 100
            theta_daily += greeks.theta * position.underlying_price * qty / 365
            vega_1pct += greeks.vega * position.underlying_price * qty / 100
        
        return PortfolioGreeks(
            total_delta=total_delta,
            total_gamma=total_gamma,
            total_theta=total_theta,
            total_vega=total_vega,
            total_rho=total_rho,
            delta_equivalent=delta_equivalent,
            gamma_dollar=gamma_dollar,
            theta_daily=theta_daily,
            vega_1pct=vega_1pct
        )
    
    def get_hedging_recommendation(self, target_delta: float = 0.0) -> Dict[str, Any]:
        """
        Get hedging recommendation to achieve target delta.
        
        Returns:
            Dict with hedging instructions
        """
        portfolio = self.get_portfolio_greeks()
        current_delta = portfolio.total_delta
        
        delta_to_hedge = target_delta - current_delta
        
        if abs(delta_to_hedge) < 0.1:
            return {
                'action': 'no_action',
                'reason': f'Current delta {current_delta:.2f} is within tolerance of target {target_delta}',
                'current_delta': current_delta,
                'target_delta': target_delta
            }
        
        # Calculate hedge size (using underlying)
        hedge_shares = -delta_to_hedge * 100  # Each option contract = 100 shares
        
        return {
            'action': 'hedge_required',
            'current_delta': current_delta,
            'target_delta': target_delta,
            'delta_to_hedge': delta_to_hedge,
            'hedge_shares': int(hedge_shares),
            'hedge_direction': 'SELL' if hedge_shares < 0 else 'BUY',
            'urgency': 'high' if abs(delta_to_hedge) > 10 else 'medium'
        }
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get comprehensive risk metrics."""
        portfolio = self.get_portfolio_greeks()
        
        return {
            'delta': portfolio.total_delta,
            'gamma': portfolio.total_gamma,
            'theta': portfolio.total_theta,
            'vega': portfolio.total_vega,
            'rho': portfolio.total_rho,
            'delta_equivalent': portfolio.delta_equivalent,
            'gamma_dollar': portfolio.gamma_dollar,
            'theta_daily': portfolio.theta_daily,
            'vega_1pct': portfolio.vega_1pct,
            'total_positions': len(self._positions),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


# Global instance
_greeks_engine: Optional[GreeksEngine] = None


def get_greeks_engine() -> GreeksEngine:
    """Get global Greeks engine instance."""
    global _greeks_engine
    if _greeks_engine is None:
        _greeks_engine = GreeksEngine()
    return _greeks_engine

