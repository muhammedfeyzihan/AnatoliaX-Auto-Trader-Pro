"""
Reinforcement Learning package for AnatoliaX Auto-Trader.

Provides RL agents and trading environments for autonomous
strategy learning and adaptation.
"""

from rl.agent import RLAgent
from rl.environment import TradingEnvironment

__all__ = [
    'RLAgent',
    'TradingEnvironment',
]

__version__ = '1.0.0'
