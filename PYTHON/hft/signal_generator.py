"""
signal_generator.py — Numba-accelerated HFT signal generation.
Supports M1 momentum and S1 micro-scalp strategies.
"""

import numpy as np
import pandas as pd
from typing import Optional

try:
    from numba import njit
    _HAS_NUMBA = True
except ImportError:
    _HAS_NUMBA = False
    # Fallback decorator
    def njit(*args, **kwargs):
        def wrapper(func):
            return func
        return wrapper


def _ema(prices: np.ndarray, period: int) -> np.ndarray:
    """Vectorized EMA."""
    if len(prices) < period:
        return prices.copy()
    alpha = 2.0 / (period + 1)
    ema = np.zeros_like(prices)
    ema[0] = prices[0]
    for i in range(1, len(prices)):
        ema[i] = alpha * prices[i] + (1 - alpha) * ema[i - 1]
    return ema


def m1_momentum_signal(
    prices: np.ndarray,
    volumes: np.ndarray,
    ema_fast: int = 3,
    ema_slow: int = 8,
    volume_mult: float = 3.0,
) -> int:
    """
    M1 Momentum Sniper signal.
    Returns: 1 (BUY), -1 (SELL), 0 (NO SIGNAL)
    """
    if len(prices) < ema_slow + 1 or len(volumes) < 20:
        return 0

    ema_f = _ema(prices, ema_fast)
    ema_s = _ema(prices, ema_slow)

    avg_volume = np.mean(volumes[-20:])
    current_volume = volumes[-1]
    volume_spike = current_volume > (avg_volume * volume_mult)

    # Crossover detection
    if ema_f[-2] <= ema_s[-2] and ema_f[-1] > ema_s[-1] and volume_spike:
        return 1
    if ema_f[-2] >= ema_s[-2] and ema_f[-1] < ema_s[-1] and volume_spike:
        return -1
    return 0


def s1_micro_scalp_signal(
    prices: np.ndarray,
    volumes: np.ndarray,
    vwap_period: int = 20,
    deviation_threshold: float = 0.001,
) -> int:
    """
    S1 Micro Scalping signal based on VWAP deviation.
    Returns: 1 (BUY - price below VWAP), -1 (SELL - price above VWAP), 0
    """
    if len(prices) < vwap_period or len(volumes) < vwap_period:
        return 0

    recent_prices = prices[-vwap_period:]
    recent_vols = volumes[-vwap_period:]

    vwap = np.sum(recent_prices * recent_vols) / np.sum(recent_vols)
    current_price = prices[-1]
    deviation = (current_price - vwap) / vwap if vwap > 0 else 0.0

    avg_vol = np.mean(volumes[-10:])
    vol_spike = volumes[-1] > avg_vol * 2.5

    if deviation < -deviation_threshold and vol_spike:
        return 1
    if deviation > deviation_threshold and vol_spike:
        return -1
    return 0


def generate_signal_from_df(
    df: pd.DataFrame,
    strategy: str = "m1_momentum",
) -> Optional[dict]:
    """
    Generate signal from a DataFrame of bars.
    Returns signal dict or None.
    """
    if df.empty or len(df) < 30:
        return None

    prices = df["close"].values
    volumes = df["volume"].values if "volume" in df.columns else np.ones(len(df))

    if strategy == "m1_momentum":
        sig = m1_momentum_signal(prices, volumes)
    elif strategy == "s1_micro_scalp":
        sig = s1_micro_scalp_signal(prices, volumes)
    else:
        return None

    if sig == 0:
        return None

    last = df.iloc[-1]
    return {
        "timestamp": last.get("timestamp", pd.Timestamp.now()),
        "signal": sig,
        "price": last["close"],
        "entry": last["close"],
        "volume": last.get("volume", 0),
        "strategy": strategy,
    }
