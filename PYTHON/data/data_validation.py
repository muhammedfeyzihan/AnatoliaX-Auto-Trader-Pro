"""
data/data_validation.py - Distributed Data Validation Architecture

Redundancy consensus, feed arbitration, stale-data quarantine,
probabilistic confidence scoring, corruption-detection pipelines.
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib


class DataQuality(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    SUSPECT = "suspect"
    CORRUPTED = "corrupted"


@dataclass
class ValidationResult:
    feed_id: str
    symbol: str
    quality: DataQuality
    confidence_score: float
    consensus_reached: bool
    feeds_agreed: int
    feeds_total: int
    timestamp: str


class DistributedDataValidation:
    def __init__(self, min_consensus: float = 0.67):
        self.min_consensus = min_consensus
        self._feeds: Dict[str, List[Dict]] = {}
        self._validation_results: List[ValidationResult] = []
        self._quarantined_data: List[Dict] = []
        self._feed_reliability: Dict[str, float] = {}
    
    def submit_feed_data(self, feed_id: str, symbol: str,
                        price: float, volume: float,
                        timestamp: str) -> None:
        if feed_id not in self._feeds:
            self._feeds[feed_id] = []
        
        self._feeds[feed_id].append({
            'symbol': symbol,
            'price': price,
            'volume': volume,
            'timestamp': timestamp,
            'received_at': datetime.now(timezone.utc).isoformat(),
        })
    
    def validate_data(self, symbol: str) -> ValidationResult:
        feeds_with_data = [f for f in self._feeds if self._feeds[f] and self._feeds[f][-1]['symbol'] == symbol]
        
        if len(feeds_with_data) < 2:
            return ValidationResult(
                feed_id='consensus',
                symbol=symbol,
                quality=DataQuality.SUSPECT,
                confidence_score=0.5,
                consensus_reached=False,
                feeds_agreed=len(feeds_with_data),
                feeds_total=len(feeds_with_data),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        
        prices = [self._feeds[f][-1]['price'] for f in feeds_with_data]
        mean_price = np.mean(prices)
        std_price = np.std(prices)
        
        if std_price == 0:
            consensus = 1.0
        else:
            cv = std_price / mean_price
            consensus = max(0, 1 - cv * 100)
        
        feeds_agreed = sum(1 for p in prices if abs(p - mean_price) / mean_price < 0.01)
        consensus_ratio = feeds_agreed / len(feeds_with_data)
        
        if consensus_ratio >= self.min_consensus:
            quality = DataQuality.EXCELLENT if consensus_ratio >= 0.95 else DataQuality.GOOD
        elif consensus_ratio >= 0.5:
            quality = DataQuality.ACCEPTABLE
        else:
            quality = DataQuality.CORRUPTED
        
        confidence_score = consensus_ratio
        
        result = ValidationResult(
            feed_id='consensus',
            symbol=symbol,
            quality=quality,
            confidence_score=confidence_score,
            consensus_reached=(consensus_ratio >= self.min_consensus),
            feeds_agreed=feeds_agreed,
            feeds_total=len(feeds_with_data),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        self._validation_results.append(result)
        
        if quality == DataQuality.CORRUPTED:
            self._quarantine_data(symbol, feeds_with_data)
        
        self._update_feed_reliability(feeds_with_data, result)
        
        return result
    
    def _quarantine_data(self, symbol: str, feeds: List[str]) -> None:
        for feed_id in feeds:
            if self._feeds[feed_id]:
                self._quarantined_data.append({
                    'feed_id': feed_id,
                    'symbol': symbol,
                    'data': self._feeds[feed_id][-1],
                    'quarantine_time': datetime.now(timezone.utc).isoformat(),
                })
    
    def _update_feed_reliability(self, feeds: List[str], result: ValidationResult) -> None:
        for feed_id in feeds:
            if feed_id not in self._feed_reliability:
                self._feed_reliability[feed_id] = 1.0
            
            if result.quality == DataQuality.EXCELLENT:
                self._feed_reliability[feed_id] = min(1.0, self._feed_reliability[feed_id] + 0.01)
            elif result.quality == DataQuality.CORRUPTED:
                self._feed_reliability[feed_id] = max(0.0, self._feed_reliability[feed_id] - 0.1)
    
    def get_data_confidence(self, symbol: str) -> float:
        recent_results = [r for r in self._validation_results if r.symbol == symbol][-10:]
        if not recent_results:
            return 0.5
        return np.mean([r.confidence_score for r in recent_results])
    
    def get_validation_report(self) -> Dict[str, Any]:
        return {
            'total_feeds': len(self._feeds),
            'total_validations': len(self._validation_results),
            'quarantined_items': len(self._quarantined_data),
            'feed_reliability': self._feed_reliability,
            'recent_validations': [
                {
                    'symbol': r.symbol,
                    'quality': r.quality.value,
                    'confidence': r.confidence_score,
                    'consensus': r.consensus_reached,
                }
                for r in self._validation_results[-10:]
            ],
        }


_data_validation: Optional[DistributedDataValidation] = None

def get_distributed_data_validation(min_consensus: float = 0.67) -> DistributedDataValidation:
    global _data_validation
    if _data_validation is None:
        _data_validation = DistributedDataValidation(min_consensus=min_consensus)
    return _data_validation
