"""
bb_volume_combo.py — Bollinger Daralma + Hacim Patlamasi Kombinasyonu
BB squeeze (bandwidth < 0.05) + hacim Z-score > 2.5 = guclu patlama sinyali.
"""
import pandas as pd
import numpy as np
from backtest import indicators


def detect_bb_volume_combo(
    df: pd.DataFrame,
    bb_period: int = 20,
    bb_std: float = 2.0,
    squeeze_threshold: float = 0.05,
    volume_z_threshold: float = 2.5,
) -> pd.DataFrame:
    """
    Bollinger squeeze ve hacim patlamasi kombinasyonunu tespit eder.

    Returns:
        df: 'BB_Squeeze', 'Vol_Spike', 'BB_Volume_Signal' kolonlari eklenmis
    """
    df = df.copy()

    # Bollinger
    df = indicators.bollinger(df, period=bb_period, std_dev=bb_std)
    df["BB_Squeeze"] = df["BB_Width"] < squeeze_threshold

    # Hacim profili
    df = indicators.volume_profile(df, period=20)
    df["Vol_Spike"] = df["Vol_ZScore"] > volume_z_threshold

    # Kombinasyon
    df["BB_Volume_Signal"] = df["BB_Squeeze"] & df["Vol_Spike"]

    # Guclu sinyal: Squeeze sonraki bar'da hacim patlamasi
    df["BB_Volume_Strong"] = (
        df["BB_Squeeze"].shift(1) &
        df["Vol_Spike"] &
        (df["close"] > df["close"].shift(1))
    )

    return df


def summarize_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Kombinasyon sinyallerini ozetler."""
    signals = df[df["BB_Volume_Signal"] == True].copy()
    if signals.empty:
        return pd.DataFrame()

    signals["Signal_Type"] = np.where(
        signals["BB_Volume_Strong"] == True,
        "STRONG_BREAKOUT",
        "SQUEEZE_SPIKE",
    )
    return signals[["close", "volume", "BB_Width", "Vol_ZScore", "Signal_Type"]]
