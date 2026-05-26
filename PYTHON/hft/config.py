"""
hft/config.py — HFT configuration and constants.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class HFTConfig:
    """HFT runtime configuration."""

    # Timeframe
    timeframe: str = "1m"  # "1m", "1s", "100ms"

    # Universe
    symbols: List[str] = None

    # Risk limits
    max_positions: int = 3
    max_trades_per_minute: int = 10
    max_daily_trades: int = 50
    max_position_value_pct: float = 0.005  # %0.5 per trade
    min_profit_target_pct: float = 0.003  # Min %0.3 net profit after costs
    max_slippage_pct: float = 0.002

    # Signal thresholds
    signal_threshold: float = 70.0
    volume_multiplier: float = 3.0

    # Broker latency budgets (ms)
    target_rtt_ms: float = 500.0
    max_rtt_ms: float = 2000.0

    # Commission + BSMV + fees
    commission_rate: float = 0.001
    bsmv_rate: float = 0.001

    # Spread filters
    max_spread_pct: float = 0.003  # Only trade if spread < 0.3%

    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["THYAO", "GARAN", "ASELS", "ISCTR", "KCHOL"]
