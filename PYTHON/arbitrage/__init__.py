"""
Arbitrage strategies package for AnatoliaX Auto-Trader.

Provides statistical arbitrage and pair selection capabilities
for multi-asset trading strategies.
"""

from arbitrage.stat_arb import StatisticalArbitrage
from arbitrage.pair_selector import PairSelector

__all__ = [
    'StatisticalArbitrage',
    'PairSelector',
]

__version__ = '1.0.0'
