"""
risk/crisis_correlation.py - Crisis Correlation Engine

Models nonlinear correlation breakdowns, contagion spread, systemic stress propagation.
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json


@dataclass
class CorrelationBreakdown:
    asset_pair: str
    normal_correlation: float
    crisis_correlation: float
    breakdown_severity: float
    timestamp: str


@dataclass
class ContagionPath:
    source_asset: str
    affected_assets: List[str]
    propagation_strength: float
    path_length: int


class CrisisCorrelationEngine:
    def __init__(self, lookback_days: int = 252):
        self.lookback_days = lookback_days
        self._normal_correlation_matrix: Dict[str, Dict[str, float]] = {}
        self._crisis_correlation_matrix: Dict[str, Dict[str, float]] = {}
        self._correlation_history: List[CorrelationBreakdown] = []
        self._contagion_paths: List[ContagionPath] = []
        self._stress_regime = False
    
    def update_normal_correlation(self, returns_data: Dict[str, List[float]]) -> None:
        assets = list(returns_data.keys())
        n = len(assets)
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                
                asset_i = assets[i]
                asset_j = assets[j]
                
                if asset_i not in self._normal_correlation_matrix:
                    self._normal_correlation_matrix[asset_i] = {}
                
                corr_i = returns_data[asset_i]
                corr_j = returns_data[asset_j]
                
                if len(corr_i) > 1 and len(corr_j) > 1:
                    correlation = np.corrcoef(corr_i, corr_j)[0, 1]
                    self._normal_correlation_matrix[asset_i][asset_j] = float(correlation)
    
    def update_crisis_correlation(self, crisis_returns: Dict[str, List[float]]) -> None:
        assets = list(crisis_returns.keys())
        n = len(assets)
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                
                asset_i = assets[i]
                asset_j = assets[j]
                
                if asset_i not in self._crisis_correlation_matrix:
                    self._crisis_correlation_matrix[asset_i] = {}
                
                corr_i = crisis_returns[asset_i]
                corr_j = crisis_returns[asset_j]
                
                if len(corr_i) > 1 and len(corr_j) > 1:
                    correlation = np.corrcoef(corr_i, corr_j)[0, 1]
                    self._crisis_correlation_matrix[asset_i][asset_j] = float(correlation)
    
    def detect_correlation_breakdown(self, threshold: float = 0.3) -> List[CorrelationBreakdown]:
        breakdowns = []
        
        for asset_i in self._normal_correlation_matrix:
            if asset_i not in self._crisis_correlation_matrix:
                continue
            
            for asset_j in self._normal_correlation_matrix[asset_i]:
                if asset_j not in self._crisis_correlation_matrix[asset_i]:
                    continue
                
                normal_corr = self._normal_correlation_matrix[asset_i][asset_j]
                crisis_corr = self._crisis_correlation_matrix[asset_i][asset_j]
                
                breakdown = abs(normal_corr - crisis_corr)
                
                if breakdown > threshold:
                    breakdowns.append(CorrelationBreakdown(
                        asset_pair=f"{asset_i}_{asset_j}",
                        normal_correlation=normal_corr,
                        crisis_correlation=crisis_corr,
                        breakdown_severity=breakdown,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    ))
        
        self._correlation_history.extend(breakdowns)
        return breakdowns
    
    def simulate_contagion(self, shock_asset: str, shock_magnitude: float) -> ContagionPath:
        affected = []
        propagation = shock_magnitude
        
        if shock_asset in self._crisis_correlation_matrix:
            for asset_j, correlation in self._crisis_correlation_matrix[shock_asset].items():
                if abs(correlation) > 0.5:
                    affected.append(asset_j)
        
        path = ContagionPath(
            source_asset=shock_asset,
            affected_assets=affected,
            propagation_strength=propagation,
            path_length=len(affected),
        )
        
        self._contagion_paths.append(path)
        return path
    
    def enable_stress_regime(self) -> None:
        self._stress_regime = True
        print('[CRISIS] Stress regime ENABLED')
    
    def disable_stress_regime(self) -> None:
        self._stress_regime = False
        print('[CRISIS] Stress regime DISABLED')
    
    def get_correlation_matrix(self, use_crisis: bool = False) -> Dict[str, Dict[str, float]]:
        if use_crisis and self._stress_regime:
            return self._crisis_correlation_matrix
        return self._normal_correlation_matrix
    
    def get_crisis_report(self) -> Dict[str, Any]:
        return {
            'stress_regime': self._stress_regime,
            'normal_correlations': len(self._normal_correlation_matrix),
            'crisis_correlations': len(self._crisis_correlation_matrix),
            'breakdowns_detected': len(self._correlation_history),
            'contagion_paths': len(self._contagion_paths),
        }


_crisis_engine: Optional[CrisisCorrelationEngine] = None

def get_crisis_correlation_engine() -> CrisisCorrelationEngine:
    global _crisis_engine
    if _crisis_engine is None:
        _crisis_engine = CrisisCorrelationEngine()
    return _crisis_engine
