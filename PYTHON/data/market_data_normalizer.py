"""
PYTHON/data/market_data_normalizer.py — Market Data Normalization Engine

CRITICAL COMPONENT #4 from Missing Components PDF

Features:
- Multi-exchange market data normalization
- Unified data schema across exchanges
- Real-time data validation
- Exchange adapter framework
- Data quality checks

Problem Statement: "Can I add a new exchange without rewriting everything?"
Without this: Each exchange requires custom code = maintenance nightmare
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Protocol
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from abc import ABC, abstractmethod


class ExchangeType(Enum):
    BIST = "bist"
    BINANCE = "binance"
    COINBASE = "coinbase"
    KRAKEN = "kraken"
    CUSTOM = "custom"


@dataclass
class NormalizedTick:
    """Normalized tick data."""
    symbol: str
    exchange: str
    price: float
    volume: float
    timestamp: datetime
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    trade_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedOrderBook:
    """Normalized orderbook data."""
    symbol: str
    exchange: str
    timestamp: datetime
    bids: List[tuple]  # [(price, size), ...]
    asks: List[tuple]
    spread: float
    mid_price: float
    depth: Dict[str, float] = field(default_factory=dict)


class ExchangeAdapter(ABC):
    """Abstract base class for exchange adapters."""
    
    @abstractmethod
    def normalize_tick(self, raw_data: Dict[str, Any]) -> NormalizedTick:
        """Convert exchange-specific tick to normalized format."""
        pass
    
    @abstractmethod
    def normalize_orderbook(self, raw_data: Dict[str, Any]) -> NormalizedOrderBook:
        """Convert exchange-specific orderbook to normalized format."""
        pass
    
    @abstractmethod
    def validate_data(self, raw_data: Dict[str, Any]) -> bool:
        """Validate raw data quality."""
        pass


class BISTAdapter(ExchangeAdapter):
    """BIST exchange adapter."""
    
    def normalize_tick(self, raw_data: Dict[str, Any]) -> NormalizedTick:
        return NormalizedTick(
            symbol=raw_data.get('symbol', ''),
            exchange='BIST',
            price=raw_data.get('price', 0.0),
            volume=raw_data.get('volume', 0.0),
            timestamp=datetime.fromisoformat(raw_data.get('timestamp', '')) if 'timestamp' in raw_data else datetime.now(timezone.utc),
            bid=raw_data.get('bid', 0.0),
            ask=raw_data.get('ask', 0.0),
            bid_size=raw_data.get('bid_size', 0.0),
            ask_size=raw_data.get('ask_size', 0.0),
            trade_id=raw_data.get('trade_id', ''),
            metadata={'exchange': 'BIST'}
        )
    
    def normalize_orderbook(self, raw_data: Dict[str, Any]) -> NormalizedOrderBook:
        bids = [(b['price'], b['size']) for b in raw_data.get('bids', [])]
        asks = [(a['price'], a['size']) for a in raw_data.get('asks', [])]
        
        mid_price = (bids[0][0] + asks[0][0]) / 2 if bids and asks else 0.0
        spread = asks[0][0] - bids[0][0] if bids and asks else 0.0
        
        return NormalizedOrderBook(
            symbol=raw_data.get('symbol', ''),
            exchange='BIST',
            timestamp=datetime.now(timezone.utc),
            bids=bids,
            asks=asks,
            spread=spread,
            mid_price=mid_price
        )
    
    def validate_data(self, raw_data: Dict[str, Any]) -> bool:
        required = ['symbol', 'price', 'volume']
        return all(k in raw_data for k in required) and raw_data.get('price', 0) > 0


class BinanceAdapter(ExchangeAdapter):
    """Binance exchange adapter."""
    
    def normalize_tick(self, raw_data: Dict[str, Any]) -> NormalizedTick:
        return NormalizedTick(
            symbol=raw_data.get('s', '').replace('USDT', ''),
            exchange='BINANCE',
            price=float(raw_data.get('p', 0)),
            volume=float(raw_data.get('q', 0)),
            timestamp=datetime.fromtimestamp(raw_data.get('T', 0) / 1000, tz=timezone.utc),
            bid=float(raw_data.get('b', 0)),
            ask=float(raw_data.get('a', 0)),
            bid_size=float(raw_data.get('B', 0)),
            ask_size=float(raw_data.get('A', 0)),
            trade_id=str(raw_data.get('t', '')),
            metadata={'exchange': 'BINANCE'}
        )
    
    def normalize_orderbook(self, raw_data: Dict[str, Any]) -> NormalizedOrderBook:
        bids = [(float(b[0]), float(b[1])) for b in raw_data.get('bids', [])]
        asks = [(float(a[0]), float(a[1])) for a in raw_data.get('asks', [])]
        
        mid_price = (bids[0][0] + asks[0][0]) / 2 if bids and asks else 0.0
        spread = asks[0][0] - bids[0][0] if bids and asks else 0.0
        
        return NormalizedOrderBook(
            symbol=raw_data.get('symbol', ''),
            exchange='BINANCE',
            timestamp=datetime.now(timezone.utc),
            bids=bids,
            asks=asks,
            spread=spread,
            mid_price=mid_price
        )
    
    def validate_data(self, raw_data: Dict[str, Any]) -> bool:
        return 's' in raw_data and 'p' in raw_data


class MarketDataNormalizer:
    """
    Market Data Normalization Engine.
    
    Provides unified interface for multi-exchange market data.
    """
    
    def __init__(self):
        self._adapters: Dict[str, ExchangeAdapter] = {
            'BIST': BISTAdapter(),
            'BINANCE': BinanceAdapter()
        }
        self._normalized_ticks: List[NormalizedTick] = []
        self._data_quality_issues: List[Dict] = []
        self._exchange_status: Dict[str, bool] = {}
    
    def register_adapter(self, exchange: str, adapter: ExchangeAdapter) -> None:
        """Register custom exchange adapter."""
        self._adapters[exchange] = adapter
    
    def normalize_tick(self, exchange: str, raw_data: Dict[str, Any]) -> Optional[NormalizedTick]:
        """Normalize tick from any exchange."""
        adapter = self._adapters.get(exchange)
        if not adapter:
            self._log_quality_issue(exchange, 'unknown_exchange', raw_data)
            return None
        
        if not adapter.validate_data(raw_data):
            self._log_quality_issue(exchange, 'invalid_data', raw_data)
            return None
        
        try:
            tick = adapter.normalize_tick(raw_data)
            self._normalized_ticks.append(tick)
            self._exchange_status[exchange] = True
            return tick
        except Exception as e:
            self._log_quality_issue(exchange, f'normalization_error: {str(e)}', raw_data)
            self._exchange_status[exchange] = False
            return None
    
    def normalize_orderbook(self, exchange: str, raw_data: Dict[str, Any]) -> Optional[NormalizedOrderBook]:
        """Normalize orderbook from any exchange."""
        adapter = self._adapters.get(exchange)
        if not adapter:
            return None
        
        try:
            return adapter.normalize_orderbook(raw_data)
        except Exception:
            return None
    
    def _log_quality_issue(self, exchange: str, issue_type: str, data: Dict) -> None:
        """Log data quality issue."""
        issue = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'exchange': exchange,
            'issue_type': issue_type,
            'data_sample': str(data)[:200]
        }
        self._data_quality_issues.append(issue)
        
        # Keep last 1000 issues
        if len(self._data_quality_issues) > 1000:
            self._data_quality_issues = self._data_quality_issues[-1000:]
    
    def get_exchange_status(self, exchange: str) -> bool:
        """Get exchange connection status."""
        return self._exchange_status.get(exchange, False)
    
    def get_all_exchanges_status(self) -> Dict[str, bool]:
        """Get all exchange statuses."""
        return self._exchange_status.copy()
    
    def get_quality_report(self) -> Dict[str, Any]:
        """Get data quality report."""
        by_exchange = {}
        by_type = {}
        
        for issue in self._data_quality_issues[-100:]:
            exch = issue['exchange']
            type_ = issue['issue_type']
            by_exchange[exch] = by_exchange.get(exch, 0) + 1
            by_type[type_] = by_type.get(type_, 0) + 1
        
        return {
            'total_issues': len(self._data_quality_issues),
            'by_exchange': by_exchange,
            'by_type': by_type,
            'exchanges_online': sum(1 for v in self._exchange_status.values() if v),
            'exchanges_offline': sum(1 for v in self._exchange_status.values() if not v)
        }
    
    def get_latest_ticks(self, symbol: str = None, limit: int = 100) -> List[NormalizedTick]:
        """Get latest normalized ticks."""
        ticks = self._normalized_ticks[-1000:]  # Keep last 1000 in memory
        
        if symbol:
            ticks = [t for t in ticks if t.symbol == symbol]
        
        return ticks[-limit:]


# Global instance
_normalizer: Optional[MarketDataNormalizer] = None


def get_market_data_normalizer() -> MarketDataNormalizer:
    """Get global normalizer instance."""
    global _normalizer
    if _normalizer is None:
        _normalizer = MarketDataNormalizer()
    return _normalizer

