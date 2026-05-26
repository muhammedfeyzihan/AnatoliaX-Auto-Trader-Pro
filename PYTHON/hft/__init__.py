"""
AnatoliaX HFT Module — High-frequency trading for BIST.

Supports 1-minute (M1), 1-second (S1), and sub-second timeframes.
Designed for BIST30 liquid stocks with broker API integration.

Key components:
- TickAggregator: sub-minute bar aggregation
- SignalGenerator: Numba-accelerated signal computation
- RiskFilter: spread, slippage, rate-limit checks
- PositionManager: lightweight in-memory position tracking
- OrderManager: microsecond-aware order lifecycle
- LatencyTracker: RTT measurement and budget enforcement
"""

__version__ = "1.0.0"
