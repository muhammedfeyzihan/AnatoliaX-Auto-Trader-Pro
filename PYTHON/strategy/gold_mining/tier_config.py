"""
tier_config.py — Gold Mining tier definitions and progression rules.

Each tier has a target profit range, holding time, max agents, and
auto-upgrade conditions. The system starts at the fastest tier
and graduates upward as capital grows.

Progression: MS → S1 → M1 → M5 → M15 → H1 → D1
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TierConfig:
    """Configuration for a single trading tier."""

    name: str                      # "MS", "S1", "M1", "M5", "M15", "H1", "D1"
    interval_seconds: float        # Bar interval in seconds
    target_profit_pct: tuple[float, float]  # (min, max) profit per trade
    holding_seconds: tuple[float, float]    # (min, max) hold time
    max_agents: int                # Max concurrent agents for this tier
    min_capital: float             # Minimum capital to unlock
    required_consecutive_wins: int # Wins needed to graduate
    required_win_rate: float       # Minimum win rate to stay in tier
    slippage_tolerance: float      # Max slippage pct accepted
    strategy_module: str           # Python module path for signal generation
    description: str = ""


# Tier progression: MS → S1 → M1 → M5 → M15 → M30 → H1 → H2 → D1
TIER_DEFINITIONS = [
    TierConfig(
        name="MS",
        interval_seconds=0.5,  # 500ms simulated
        target_profit_pct=(0.01, 0.05),  # 0.01-0.05%
        holding_seconds=(0.5, 3.0),     # 500ms - 3s
        max_agents=1,
        min_capital=0.0,        # Always available
        required_consecutive_wins=5,
        required_win_rate=0.55,
        slippage_tolerance=0.001,
        strategy_module="strategy.gold_mining.ms_strategy",
        description="Millisecond order-flow imbalance scalping. Highest frequency, lowest per-trade profit.",
    ),
    TierConfig(
        name="S1",
        interval_seconds=1.0,
        target_profit_pct=(0.05, 0.2),
        holding_seconds=(3.0, 15.0),
        max_agents=1,
        min_capital=1_000.0,    # 1,000 TL profit needed
        required_consecutive_wins=5,
        required_win_rate=0.55,
        slippage_tolerance=0.002,
        strategy_module="strategy.gold_mining.s1_strategy",
        description="1-second VWAP deviation + volume spike. Fast execution required.",
    ),
    TierConfig(
        name="M1",
        interval_seconds=60.0,
        target_profit_pct=(0.3, 1.0),
        holding_seconds=(30.0, 120.0),
        max_agents=2,
        min_capital=5_000.0,    # 5,000 TL profit needed
        required_consecutive_wins=5,
        required_win_rate=0.55,
        slippage_tolerance=0.003,
        strategy_module="strategy.gold_mining.m1_strategy",
        description="1-minute EMA 3/8 cross + volume breakout. 2-agent coordination.",
    ),
    TierConfig(
        name="M5",
        interval_seconds=300.0,
        target_profit_pct=(0.8, 2.0),
        holding_seconds=(120.0, 600.0),
        max_agents=2,
        min_capital=12_000.0,   # 12,000 TL profit needed
        required_consecutive_wins=4,
        required_win_rate=0.57,
        slippage_tolerance=0.004,
        strategy_module="strategy.gold_mining.m5_strategy",
        description="5-minute EMA 5/13 cross + volume + ATR filter. 2-agent confirmation.",
    ),
    TierConfig(
        name="M15",
        interval_seconds=900.0,
        target_profit_pct=(1.5, 5.0),
        holding_seconds=(300.0, 1800.0),
        max_agents=3,
        min_capital=25_000.0,   # 25,000 TL profit needed
        required_consecutive_wins=3,
        required_win_rate=0.60,
        slippage_tolerance=0.005,
        strategy_module="strategy.gold_mining.m15_strategy",
        description="15-minute multi-agent swing. Full 3-agent council with consensus.",
    ),
    TierConfig(
        name="M30",
        interval_seconds=1800.0,
        target_profit_pct=(2.5, 7.0),
        holding_seconds=(1800.0, 7200.0),
        max_agents=3,
        min_capital=37_500.0,   # 37,500 TL profit needed
        required_consecutive_wins=3,
        required_win_rate=0.60,
        slippage_tolerance=0.006,
        strategy_module="strategy.gold_mining.m30_strategy",
        description="30-minute trend continuation. EMA 13/34 + 3-agent consensus with ParameterRegistry.",
    ),
    TierConfig(
        name="H1",
        interval_seconds=3600.0,
        target_profit_pct=(2.0, 6.0),
        holding_seconds=(3600.0, 14400.0),
        max_agents=3,
        min_capital=50_000.0,   # 50,000 TL profit needed
        required_consecutive_wins=3,
        required_win_rate=0.60,
        slippage_tolerance=0.008,
        strategy_module="strategy.gold_mining.h1_strategy",
        description="1-hour trend strategy. EMA 9/21 + MACD + 3-agent consensus.",
    ),
    TierConfig(
        name="H2",
        interval_seconds=7200.0,
        target_profit_pct=(4.0, 10.0),
        holding_seconds=(7200.0, 28800.0),
        max_agents=3,
        min_capital=75_000.0,   # 75,000 TL profit needed
        required_consecutive_wins=2,
        required_win_rate=0.62,
        slippage_tolerance=0.009,
        strategy_module="strategy.gold_mining.h2_strategy",
        description="2-hour macro trend. EMA 21/55 + RSI + BB + 3-agent consensus with ParameterRegistry.",
    ),
    TierConfig(
        name="D1",
        interval_seconds=86400.0,
        target_profit_pct=(5.0, 15.0),
        holding_seconds=(86400.0, 432000.0),
        max_agents=3,
        min_capital=100_000.0,  # 100,000 TL profit needed
        required_consecutive_wins=2,
        required_win_rate=0.62,
        slippage_tolerance=0.010,
        strategy_module="strategy.gold_mining.d1_strategy",
        description="1-day position strategy. EMA 21/50 + RSI + BB + 3-agent consensus.",
    ),
]


def get_tier_by_name(name: str) -> Optional[TierConfig]:
    for tier in TIER_DEFINITIONS:
        if tier.name == name:
            return tier
    return None


def get_next_tier(current_name: str) -> Optional[TierConfig]:
    names = [t.name for t in TIER_DEFINITIONS]
    try:
        idx = names.index(current_name)
        if idx + 1 < len(TIER_DEFINITIONS):
            return TIER_DEFINITIONS[idx + 1]
    except ValueError:
        pass
    return None


def get_default_tier() -> TierConfig:
    return TIER_DEFINITIONS[0]
