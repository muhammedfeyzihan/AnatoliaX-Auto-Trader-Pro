"""
risk/portfolio_optimizer_pro.py - Institutional Portfolio Optimizer

Black-Litterman allocation, robust mean-variance optimization,
regime-sensitive covariance adjustment, dynamic cross-asset exposure balancing.
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from scipy.optimize import minimize


@dataclass
class PortfolioWeights:
    assets: List[str]
    weights: np.ndarray
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    optimization_method: str
    timestamp: str


class InstitutionalPortfolioOptimizer:
    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate
        self._expected_returns: Dict[str, float] = {}
        self._covariance_matrix: Optional[np.ndarray] = None
        self._views: List[Dict] = []
        self._market_caps: Dict[str, float] = {}
        self._optimization_history: List[PortfolioWeights] = []
    
    def black_litterman_optimization(self, assets: List[str],
                                    market_caps: Dict[str, float],
                                    views: List[Dict],
                                    covariance: np.ndarray,
                                    tau: float = 0.05,
                                    risk_aversion: float = 2.5) -> PortfolioWeights:
        n = len(assets)
        
        weights_market = np.array([market_caps.get(a, 1.0) for a in assets])
        weights_market = weights_market / weights_market.sum()
        
        implied_returns = risk_aversion * covariance @ weights_market
        
        if len(views) == 0:
            posterior_returns = implied_returns
        else:
            k = len(views)
            P = np.zeros((k, n))
            Q = np.zeros(k)
            omega = np.zeros((k, k))
            
            for i, view in enumerate(views):
                if view['type'] == 'absolute':
                    P[i, assets.index(view['asset'])] = 1
                    Q[i] = view['expected_return']
                elif view['type'] == 'relative':
                    P[i, assets.index(view['asset_long'])] = 1
                    P[i, assets.index(view['asset_short'])] = -1
                    Q[i] = view['expected_return_diff']
                omega[i, i] = view['uncertainty']
            
            tau_sigma = tau * covariance
            M1 = np.linalg.inv(np.linalg.inv(tau_sigma) + P.T @ np.linalg.inv(omega) @ P)
            M2 = np.linalg.inv(tau_sigma) @ implied_returns + P.T @ np.linalg.inv(omega) @ Q
            posterior_returns = M1 @ M2
        
        weights = self._optimize_weights(posterior_returns, covariance)
        
        expected_return = float(weights @ posterior_returns)
        expected_vol = float(np.sqrt(weights @ covariance @ weights))
        sharpe = (expected_return - self.risk_free_rate) / (expected_vol + 1e-6)
        
        result = PortfolioWeights(
            assets=assets,
            weights=weights,
            expected_return=expected_return,
            expected_volatility=expected_vol,
            sharpe_ratio=sharpe,
            optimization_method="black_litterman",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        self._optimization_history.append(result)
        return result
    
    def robust_mean_variance(self, assets: List[str],
                            expected_returns: np.ndarray,
                            covariance: np.ndarray,
                            target_return: Optional[float] = None) -> PortfolioWeights:
        n = len(assets)
        
        def objective(weights):
            return weights @ covariance @ weights
        
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
        
        if target_return is not None:
            constraints.append({
                'type': 'eq',
                'fun': lambda w: w @ expected_returns - target_return
            })
        
        bounds = tuple((0, 1) for _ in range(n))
        x0 = np.ones(n) / n
        
        result = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)
        weights = result.x
        weights = np.maximum(weights, 0)
        weights = weights / weights.sum()
        
        exp_ret = float(weights @ expected_returns)
        exp_vol = float(np.sqrt(weights @ covariance @ weights))
        sharpe = (exp_ret - self.risk_free_rate) / (exp_vol + 1e-6)
        
        portfolio = PortfolioWeights(
            assets=assets,
            weights=weights,
            expected_return=exp_ret,
            expected_volatility=exp_vol,
            sharpe_ratio=sharpe,
            optimization_method="robust_mean_variance",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        self._optimization_history.append(portfolio)
        return portfolio
    
    def _optimize_weights(self, returns: np.ndarray,
                         covariance: np.ndarray) -> np.ndarray:
        n = len(returns)
        
        def negative_sharpe(weights):
            ret = weights @ returns
            vol = np.sqrt(weights @ covariance @ weights)
            return -(ret - self.risk_free_rate) / (vol + 1e-6)
        
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
        bounds = tuple((0, 1) for _ in range(n))
        x0 = np.ones(n) / n
        
        result = minimize(negative_sharpe, x0, method='SLSQP', bounds=bounds, constraints=constraints)
        weights = result.x
        weights = np.maximum(weights, 0)
        weights = weights / weights.sum()
        
        return weights
    
    def add_view(self, view_type: str, **kwargs) -> None:
        self._views.append({
            'type': view_type,
            **kwargs,
        })
    
    def clear_views(self) -> None:
        self._views = []
    
    def get_optimizer_report(self) -> Dict[str, Any]:
        if not self._optimization_history:
            return {'error': 'No optimizations performed'}
        
        latest = self._optimization_history[-1]
        
        return {
            'total_optimizations': len(self._optimization_history),
            'latest_method': latest.optimization_method,
            'latest_sharpe': latest.sharpe_ratio,
            'latest_return': latest.expected_return,
            'latest_volatility': latest.expected_volatility,
            'active_views': len(self._views),
            'assets_tracked': len(latest.assets),
        }


_portfolio_optimizer_pro: Optional[InstitutionalPortfolioOptimizer] = None

def get_institutional_portfolio_optimizer(risk_free_rate: float = 0.02) -> InstitutionalPortfolioOptimizer:
    global _portfolio_optimizer_pro
    if _portfolio_optimizer_pro is None:
        _portfolio_optimizer_pro = InstitutionalPortfolioOptimizer(risk_free_rate=risk_free_rate)
    return _portfolio_optimizer_pro
