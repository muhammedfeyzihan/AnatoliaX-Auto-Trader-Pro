"""
execution/liquidity_intelligence.py - Real-time Liquidity Intelligence Engine

Detects spoofing, iceberg orders, liquidity vacuums, hidden orderflow,
toxic flow, execution traps, institutional accumulation/distribution.
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib


class LiquiditySignal(Enum):
    NORMAL = "normal"
    SPOOFING_DETECTED = "spoofing_detected"
    ICEBERG_ORDER = "iceberg_order"
    LIQUIDITY_VACUUM = "liquidity_vacuum"
    HIDDEN_ORDERFLOW = "hidden_orderflow"
    TOXIC_FLOW = "toxic_flow"
    EXECUTION_TRAP = "execution_trap"
    INSTITUTIONAL_ACCUMULATION = "institutional_accumulation"
    INSTITUTIONAL_DISTRIBUTION = "institutional_distribution"


@dataclass
class LiquidityAlert:
    alert_id: str
    signal_type: LiquiditySignal
    symbol: str
    confidence: float
    evidence: List[str]
    timestamp: str
    action_recommended: str


@dataclass
class OrderBookImbalance:
    symbol: str
    bid_volume: float
    ask_volume: float
    imbalance_ratio: float
    spoofing_score: float
    iceberg_probability: float
    timestamp: str


class LiquidityIntelligenceEngine:
    def __init__(self, lookback_ticks: int = 100):
        self.lookback_ticks = lookback_ticks
        self._orderbook_history: Dict[str, List[Dict]] = {}
        self._trade_history: Dict[str, List[Dict]] = {}
        self._alerts: List[LiquidityAlert] = []
        self._imbalance_metrics: Dict[str, OrderBookImbalance] = {}
        self._vpin_scores: Dict[str, float] = {}
    
    def analyze_orderbook(self, symbol: str, 
                         bids: List[Tuple[float, float]],
                         asks: List[Tuple[float, float]]) -> OrderBookImbalance:
        bid_volume = sum(size for price, size in bids)
        ask_volume = sum(size for price, size in asks)
        
        total_volume = bid_volume + ask_volume + 1e-6
        imbalance_ratio = (bid_volume - ask_volume) / total_volume
        
        spoofing_score = self._detect_spoofing(symbol, bids, asks)
        iceberg_prob = self._detect_iceberg(symbol, bids, asks)
        
        imbalance = OrderBookImbalance(
            symbol=symbol,
            bid_volume=bid_volume,
            ask_volume=ask_volume,
            imbalance_ratio=imbalance_ratio,
            spoofing_score=spoofing_score,
            iceberg_probability=iceberg_prob,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        self._imbalance_metrics[symbol] = imbalance
        self._check_liquidity_vacuum(symbol, bids, asks)
        
        return imbalance
    
    def _detect_spoofing(self, symbol: str,
                        bids: List[Tuple[float, float]],
                        asks: List[Tuple[float, float]]) -> float:
        if len(bids) < 3 or len(asks) < 3:
            return 0.0
        
        bid_sizes = [size for price, size in bids]
        ask_sizes = [size for price, size in asks]
        
        bid_ratio = max(bid_sizes) / (np.mean(bid_sizes) + 1e-6)
        ask_ratio = max(ask_sizes) / (np.mean(ask_sizes) + 1e-6)
        
        spoofing_score = max(0.0, min(1.0, (max(bid_ratio, ask_ratio) - 3.0) / 7.0))
        
        if spoofing_score > 0.5:
            self._create_alert(
                symbol=symbol,
                signal_type=LiquiditySignal.SPOOFING_DETECTED,
                confidence=spoofing_score,
                evidence=[f"Bid ratio: {bid_ratio:.2f}", f"Ask ratio: {ask_ratio:.2f}"],
                action_recommended="Widen spread, reduce order size",
            )
        
        return spoofing_score
    
    def _detect_iceberg(self, symbol: str,
                       bids: List[Tuple[float, float]],
                       asks: List[Tuple[float, float]]) -> float:
        if symbol not in self._trade_history:
            return 0.0
        
        trades = self._trade_history[symbol][-50:]
        if len(trades) < 10:
            return 0.0
        
        trade_sizes = [t['size'] for t in trades]
        avg_size = np.mean(trade_sizes)
        
        repeated_sizes = sum(1 for i in range(len(trade_sizes)-1) 
                           if abs(trade_sizes[i] - trade_sizes[i+1]) < avg_size * 0.1)
        
        iceberg_prob = min(1.0, repeated_sizes / (len(trade_sizes) + 1e-6))
        
        if iceberg_prob > 0.6:
            self._create_alert(
                symbol=symbol,
                signal_type=LiquiditySignal.ICEBERG_ORDER,
                confidence=iceberg_prob,
                evidence=[f"Repeated trade sizes: {repeated_sizes}"],
                action_recommended="Use iceberg detection in execution",
            )
        
        return iceberg_prob
    
    def _check_liquidity_vacuum(self, symbol: str,
                               bids: List[Tuple[float, float]],
                               asks: List[Tuple[float, float]]) -> None:
        total_liquidity = sum(size for price, size in bids) + sum(size for price, size in asks)
        
        if symbol in self._orderbook_history:
            history = self._orderbook_history[symbol][-10:]
            if len(history) > 0:
                avg_liquidity = np.mean([
                    h['bid_volume'] + h['ask_volume'] 
                    for h in history if 'bid_volume' in h
                ])
                
                if total_liquidity < avg_liquidity * 0.3:
                    self._create_alert(
                        symbol=symbol,
                        signal_type=LiquiditySignal.LIQUIDITY_VACUUM,
                        confidence=0.8,
                        evidence=[f"Liquidity dropped to {total_liquidity/avg_liquidity*100:.1f}% of average"],
                        action_recommended="Pause trading, wait for liquidity recovery",
                    )
    
    def analyze_trade(self, symbol: str, price: float, 
                     size: float, side: str) -> Optional[LiquidityAlert]:
        if symbol not in self._trade_history:
            self._trade_history[symbol] = []
        
        self._trade_history[symbol].append({
            'price': price,
            'size': size,
            'side': side,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
        
        vpin = self._calculate_vpin(symbol)
        self._vpin_scores[symbol] = vpin
        
        if vpin > 0.7:
            return self._create_alert(
                symbol=symbol,
                signal_type=LiquiditySignal.TOXIC_FLOW,
                confidence=vpin,
                evidence=[f"VPIN score: {vpin:.2f}"],
                action_recommended="Reduce position size, widen stops",
            )
        
        return None
    
    def _calculate_vpin(self, symbol: str) -> float:
        if symbol not in self._trade_history or len(self._trade_history[symbol]) < 50:
            return 0.0
        
        trades = self._trade_history[symbol][-50:]
        buy_volume = sum(t['size'] for t in trades if t['side'] == 'buy')
        sell_volume = sum(t['size'] for t in trades if t['side'] == 'sell')
        total_volume = buy_volume + sell_volume + 1e-6
        
        vpin = abs(buy_volume - sell_volume) / total_volume
        return vpin
    
    def detect_hidden_orderflow(self, symbol: str,
                               price_changes: List[float],
                               volumes: List[float]) -> Optional[LiquidityAlert]:
        if len(price_changes) < 20:
            return None
        
        correlation = np.corrcoef(price_changes[-20:], volumes[-20:])[0, 1]
        
        if abs(correlation) < 0.2 and np.std(price_changes[-20:]) > 0.01:
            return self._create_alert(
                symbol=symbol,
                signal_type=LiquiditySignal.HIDDEN_ORDERFLOW,
                confidence=0.7,
                evidence=[f"Price-volume correlation: {correlation:.2f}"],
                action_recommended="Monitor for institutional activity",
            )
        
        return None
    
    def detect_institutional_activity(self, symbol: str,
                                     large_trades: List[Dict]) -> Optional[LiquidityAlert]:
        if len(large_trades) < 5:
            return None
        
        buy_large = sum(1 for t in large_trades if t['side'] == 'buy' and t['size'] > 10000)
        sell_large = sum(1 for t in large_trades if t['side'] == 'sell' and t['size'] > 10000)
        
        if buy_large > sell_large * 2:
            return self._create_alert(
                symbol=symbol,
                signal_type=LiquiditySignal.INSTITUTIONAL_ACCUMULATION,
                confidence=0.8,
                evidence=[f"Large buys: {buy_large}, Large sells: {sell_large}"],
                action_recommended="Consider long position",
            )
        elif sell_large > buy_large * 2:
            return self._create_alert(
                symbol=symbol,
                signal_type=LiquiditySignal.INSTITUTIONAL_DISTRIBUTION,
                confidence=0.8,
                evidence=[f"Large sells: {sell_large}, Large buys: {buy_large}"],
                action_recommended="Consider reducing position",
            )
        
        return None
    
    def _create_alert(self, symbol: str, signal_type: LiquiditySignal,
                     confidence: float, evidence: List[str],
                     action_recommended: str) -> LiquidityAlert:
        alert_id = hashlib.sha256(
            f"{symbol}{signal_type.value}{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:16]
        
        alert = LiquidityAlert(
            alert_id=alert_id,
            signal_type=signal_type,
            symbol=symbol,
            confidence=confidence,
            evidence=evidence,
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_recommended=action_recommended,
        )
        
        self._alerts.append(alert)
        print(f"[LIQUIDITY] {signal_type.value} on {symbol}: {confidence:.2f}")
        return alert
    
    def get_liquidity_report(self, symbol: str) -> Dict[str, Any]:
        report = {
            'symbol': symbol,
            'alerts_count': len([a for a in self._alerts if a.symbol == symbol]),
            'vpin_score': self._vpin_scores.get(symbol, 0.0),
        }
        
        if symbol in self._imbalance_metrics:
            imb = self._imbalance_metrics[symbol]
            report.update({
                'bid_volume': imb.bid_volume,
                'ask_volume': imb.ask_volume,
                'imbalance_ratio': imb.imbalance_ratio,
                'spoofing_score': imb.spoofing_score,
                'iceberg_probability': imb.iceberg_probability,
            })
        
        return report
    
    def get_global_liquidity_report(self) -> Dict[str, Any]:
        return {
            'total_alerts': len(self._alerts),
            'symbols_monitored': len(self._imbalance_metrics),
            'alerts_by_type': self._count_alerts_by_type(),
            'recent_alerts': [
                {
                    'symbol': a.symbol,
                    'type': a.signal_type.value,
                    'confidence': a.confidence,
                }
                for a in self._alerts[-10:]
            ],
        }
    
    def _count_alerts_by_type(self) -> Dict[str, int]:
        counts = {}
        for alert in self._alerts:
            key = alert.signal_type.value
            if key not in counts:
                counts[key] = 0
            counts[key] += 1
        return counts


_liquidity_engine: Optional[LiquidityIntelligenceEngine] = None

def get_liquidity_intelligence() -> LiquidityIntelligenceEngine:
    global _liquidity_engine
    if _liquidity_engine is None:
        _liquidity_engine = LiquidityIntelligenceEngine()
    return _liquidity_engine
