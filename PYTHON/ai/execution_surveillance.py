"""
ai/execution_surveillance.py - AI-Driven Execution Surveillance System

Behavioral anomaly detection, execution-quality scoring, latency drift analysis,
broker-performance ranking, trade-forensics monitoring.
"""

import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict


@dataclass
class ExecutionQualityScore:
    trade_id: str
    broker: str
    symbol: str
    quality_score: float
    latency_score: float
    slippage_score: float
    fill_rate_score: float
    timestamp: str


@dataclass
class BrokerRanking:
    broker_name: str
    avg_quality_score: float
    total_trades: int
    avg_latency_ms: float
    avg_slippage_bps: float
    fill_rate: float
    rank: int


class ExecutionSurveillanceSystem:
    def __init__(self):
        self._executions: List[Dict] = []
        self._broker_metrics: Dict[str, Dict] = defaultdict(lambda: {
            'trades': [],
            'latencies': [],
            'slippages': [],
            'fill_rates': [],
        })
        self._quality_scores: List[ExecutionQualityScore] = []
        self._anomalies: List[Dict] = []
    
    def record_execution(self, trade_id: str, broker: str, symbol: str,
                        side: str, quantity: float, arrival_price: float,
                        fill_price: float, fill_quantity: float,
                        latency_ms: float) -> ExecutionQualityScore:
        fill_rate = fill_quantity / quantity if quantity > 0 else 0
        slippage = (fill_price - arrival_price) / arrival_price * 10000
        if side == 'sell':
            slippage = -slippage
        
        execution = {
            'trade_id': trade_id,
            'broker': broker,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'arrival_price': arrival_price,
            'fill_price': fill_price,
            'fill_quantity': fill_quantity,
            'latency_ms': latency_ms,
            'slippage_bps': slippage,
            'fill_rate': fill_rate,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        
        self._executions.append(execution)
        self._broker_metrics[broker]['trades'].append(execution)
        self._broker_metrics[broker]['latencies'].append(latency_ms)
        self._broker_metrics[broker]['slippages'].append(slippage)
        self._broker_metrics[broker]['fill_rates'].append(fill_rate)
        
        quality_score = self._calculate_quality_score(execution)
        self._quality_scores.append(quality_score)
        
        self._detect_anomalies(execution)
        
        return quality_score
    
    def _calculate_quality_score(self, execution: Dict) -> ExecutionQualityScore:
        latency_score = max(0, 100 - execution['latency_ms'] / 10)
        slippage_score = max(0, 100 - abs(execution['slippage_bps']) / 2)
        fill_rate_score = execution['fill_rate'] * 100
        
        quality_score = (latency_score * 0.3 + slippage_score * 0.4 + fill_rate_score * 0.3)
        
        return ExecutionQualityScore(
            trade_id=execution['trade_id'],
            broker=execution['broker'],
            symbol=execution['symbol'],
            quality_score=quality_score,
            latency_score=latency_score,
            slippage_score=slippage_score,
            fill_rate_score=fill_rate_score,
            timestamp=execution['timestamp'],
        )
    
    def _detect_anomalies(self, execution: Dict) -> None:
        broker = execution['broker']
        metrics = self._broker_metrics[broker]
        
        if len(metrics['latencies']) >= 10:
            lat_mean = np.mean(metrics['latencies'][:-1])
            lat_std = np.std(metrics['latencies'][:-1])
            if lat_std > 0 and abs(execution['latency_ms'] - lat_mean) > 3 * lat_std:
                self._anomalies.append({
                    'type': 'latency_drift',
                    'broker': broker,
                    'value': execution['latency_ms'],
                    'expected': lat_mean,
                    'timestamp': execution['timestamp'],
                })
        
        if len(metrics['slippages']) >= 10:
            slip_mean = np.mean(metrics['slippages'][:-1])
            slip_std = np.std(metrics['slippages'][:-1])
            if slip_std > 0 and abs(execution['slippage_bps']) > abs(slip_mean) + 3 * slip_std:
                self._anomalies.append({
                    'type': 'slippage_anomaly',
                    'broker': broker,
                    'value': execution['slippage_bps'],
                    'expected': slip_mean,
                    'timestamp': execution['timestamp'],
                })
    
    def get_broker_rankings(self) -> List[BrokerRanking]:
        rankings = []
        
        for broker, metrics in self._broker_metrics.items():
            if len(metrics['trades']) == 0:
                continue
            
            avg_quality = np.mean([q.quality_score for q in self._quality_scores if q.broker == broker])
            avg_latency = np.mean(metrics['latencies']) if metrics['latencies'] else 0
            avg_slippage = np.mean(metrics['slippages']) if metrics['slippages'] else 0
            avg_fill_rate = np.mean(metrics['fill_rates']) if metrics['fill_rates'] else 0
            
            rankings.append(BrokerRanking(
                broker_name=broker,
                avg_quality_score=avg_quality,
                total_trades=len(metrics['trades']),
                avg_latency_ms=avg_latency,
                avg_slippage_bps=avg_slippage,
                fill_rate=avg_fill_rate,
                rank=0,
            ))
        
        rankings.sort(key=lambda r: r.avg_quality_score, reverse=True)
        for i, r in enumerate(rankings):
            r.rank = i + 1
        
        return rankings
    
    def get_surveillance_report(self) -> Dict[str, Any]:
        return {
            'total_executions': len(self._executions),
            'brokers_monitored': len(self._broker_metrics),
            'anomalies_detected': len(self._anomalies),
            'broker_rankings': [
                {
                    'rank': r.rank,
                    'broker': r.broker_name,
                    'quality_score': r.avg_quality_score,
                    'trades': r.total_trades,
                }
                for r in self.get_broker_rankings()
            ],
            'recent_anomalies': self._anomalies[-10:],
        }


_execution_surveillance: Optional[ExecutionSurveillanceSystem] = None

def get_execution_surveillance() -> ExecutionSurveillanceSystem:
    global _execution_surveillance
    if _execution_surveillance is None:
        _execution_surveillance = ExecutionSurveillanceSystem()
    return _execution_surveillance
