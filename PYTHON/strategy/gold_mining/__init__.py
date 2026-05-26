"""
AnatoliaX Gold Mining Strategy

Kademeli agent aktivasyonlu, multi-timeframe scalping motoru.
MS → S1 → M1 → M15 zaman dilimlerinde otomatik geçiş.
Maksimum 3 agent, minimum risk, profesyonel verim.

Usage:
    from strategy.gold_mining.orchestrator import GoldMiningOrchestrator
    engine = GoldMiningOrchestrator()
    engine.run(symbols=["THYAO", "GARAN"])
"""

from strategy.gold_mining.tier_config import (
    TierConfig,
    TIER_DEFINITIONS,
    get_tier_by_name,
    get_next_tier,
    get_default_tier,
)
from strategy.gold_mining.ms_strategy import MSStrategy
from strategy.gold_mining.s1_strategy import S1Strategy
from strategy.gold_mining.m1_strategy import M1Strategy
from strategy.gold_mining.m5_strategy import M5Strategy
from strategy.gold_mining.m15_strategy import M15Strategy
from strategy.gold_mining.h1_strategy import H1Strategy
from strategy.gold_mining.d1_strategy import D1Strategy
from strategy.gold_mining.adaptive_selector import AdaptiveTierSelector
from strategy.gold_mining.orchestrator import (
    GoldMiningOrchestrator,
    GoldMiningState,
)

__all__ = [
    "TierConfig",
    "TIER_DEFINITIONS",
    "get_tier_by_name",
    "get_next_tier",
    "get_default_tier",
    "MSStrategy",
    "S1Strategy",
    "M1Strategy",
    "M5Strategy",
    "M15Strategy",
    "H1Strategy",
    "D1Strategy",
    "AdaptiveTierSelector",
    "GoldMiningOrchestrator",
    "GoldMiningState",
]
