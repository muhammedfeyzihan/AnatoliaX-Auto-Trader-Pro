"""
execution/slippage_tca.py - Probabilistic Slippage & Transaction Cost Analysis

Market-impact modeling, Almgren-Chriss execution mathematics,
spread-volatility estimation, adaptive execution cost forecasting.
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class SlippageEstimate:
    symbol: str
    arrival_price: float
    expected_slippage: float
    slippage_std: float
    market_impact: float
    timing_cost: float
    spread_cost: float
    confidence_interval_95: Tuple[float, float]
    timestamp: str


@dataclass
class TCAReport:
    trade_id: str
    symbol: str
    side: str
    quantity: float
    arrival_price: float
    avg_execution_price: float
    total_slippage: float
    market_impact: float
    timing_cost: float
    spread_cost: float
    commission: float
    total_tca: float
    benchmark: str
    timestamp: str


class SlippageTCAEngine:
    def __init__(self):
        self._historical_slippage: Dict[str, List[float]] = {}
        self._market_impact_params: Dict[str, Dict] = {}
        self._tca_reports: List[TCAReport] = []
    
    def estimate_slippage_almgren_chriss(self, symbol: str,
                                        quantity: float,
                                        arrival_price: float,
                                        volatility: float,
                                        daily_volume: float,
                                        participation_rate: float,
                                        risk_aversion: float = 0.5) -> SlippageEstimate:
        b = self._get_market_impact_param(symbol)
        
        market_impact = b * (quantity / daily_volume) * arrival_price
        
        timing_risk = risk_aversion * volatility * arrival_price * np.sqrt(participation_rate)
        
        spread_cost = arrival_price * 0.001
        
        expected_slippage = market_impact + timing_risk + spread_cost
        
        slippage_std = expected_slippage * 0.3
        
        ci_lower = expected_slippage - 1.96 * slippage_std
        ci_upper = expected_slippage + 1.96 * slippage_std
        
        estimate = SlippageEstimate(
            symbol=symbol,
            arrival_price=arrival_price,
            expected_slippage=expected_slippage,
            slippage_std=slippage_std,
            market_impact=market_impact,
            timing_cost=timing_risk,
            spread_cost=spread_cost,
            confidence_interval_95=(max(0, ci_lower), ci_upper),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        return estimate
    
    def calculate_market_impact(self, symbol: str,
                               quantity: float,
                               price: float,
                               volume: float) -> float:
        b = self._get_market_impact_param(symbol)
        return b * (quantity / volume) * price
    
    def _get_market_impact_param(self, symbol: str) -> float:
        if symbol in self._market_impact_params:
            return self._market_impact_params[symbol].get('b', 0.1)
        
        return 0.1
    
    def update_market_impact_param(self, symbol: str,
                                   realized_impact: float,
                                   quantity: float,
                                   volume: float,
                                   price: float) -> None:
        if quantity > 0 and volume > 0 and price > 0:
            realized_b = realized_impact / ((quantity / volume) * price)
            
            if symbol not in self._market_impact_params:
                self._market_impact_params[symbol] = {'b': realized_b, 'observations': 1}
            else:
                params = self._market_impact_params[symbol]
                params['b'] = params['b'] * 0.9 + realized_b * 0.1
                params['observations'] += 1
    
    def record_execution(self, trade_id: str, symbol: str, side: str,
                        quantity: float, arrival_price: float,
                        execution_price: float, commission: float = 0.0) -> TCAReport:
        total_slippage = (execution_price - arrival_price) / arrival_price
        if side == 'sell':
            total_slippage = -total_slippage
        
        spread_cost = arrival_price * 0.001
        market_impact = total_slippage * 0.6
        timing_cost = total_slippage * 0.4
        
        total_tca = abs(total_slippage) + commission
        
        report = TCAReport(
            trade_id=trade_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            arrival_price=arrival_price,
            avg_execution_price=execution_price,
            total_slippage=total_slippage,
            market_impact=market_impact,
            timing_cost=timing_cost,
            spread_cost=spread_cost,
            commission=commission,
            total_tca=total_tca,
            benchmark='arrival_price',
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        self._tca_reports.append(report)
        
        if symbol not in self._historical_slippage:
            self._historical_slippage[symbol] = []
        self._historical_slippage[symbol].append(total_slippage)
        
        self.update_market_impact_param(symbol, market_impact, quantity, 1000000, arrival_price)
        
        return report
    
    def get_tca_summary(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        reports = self._tca_reports
        if symbol:
            reports = [r for r in reports if r.symbol == symbol]
        
        if not reports:
            return {'error': 'No TCA data'}
        
        total_slippage = np.mean([r.total_slippage for r in reports])
        total_market_impact = np.mean([r.market_impact for r in reports])
        total_timing_cost = np.mean([r.timing_cost for r in reports])
        total_commission = np.sum([r.commission for r in reports])
        
        return {
            'total_trades': len(reports),
            'avg_slippage_bps': total_slippage * 10000,
            'avg_market_impact_bps': total_market_impact * 10000,
            'avg_timing_cost_bps': total_timing_cost * 10000,
            'total_commission': total_commission,
            'total_tca_bps': (total_slippage + total_commission) * 10000,
        }
    
    def get_slippage_distribution(self, symbol: str) -> Dict[str, Any]:
        if symbol not in self._historical_slippage or len(self._historical_slippage[symbol]) == 0:
            return {'error': 'No data'}
        
        slippages = self._historical_slippage[symbol]
        
        return {
            'symbol': symbol,
            'count': len(slippages),
            'mean': np.mean(slippages),
            'std': np.std(slippages),
            'median': np.median(slippages),
            'min': np.min(slippages),
            'max': np.max(slippages),
            'percentile_95': np.percentile(slippages, 95),
            'percentile_99': np.percentile(slippages, 99),
        }


_slippage_tca: Optional[SlippageTCAEngine] = None

def get_slippage_tca_engine() -> SlippageTCAEngine:
    global _slippage_tca
    if _slippage_tca is None:
        _slippage_tca = SlippageTCAEngine()
    return _slippage_tca
