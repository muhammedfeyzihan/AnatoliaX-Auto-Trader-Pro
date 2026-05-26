"""
volume_anomaly.py — Hacim Profili Anomalisi Tespiti (Z-score > 3)
Ani hacim patlamalarini tespit eder — manipulasyon veya onemli hareket sinyali.
"""
import pandas as pd
import numpy as np


def detect_volume_anomaly(
    df: pd.DataFrame,
    period: int = 20,
    z_threshold: float = 3.0,
    min_volume_ratio: float = 2.5,
) -> pd.DataFrame:
    """
    Hacim Z-skoru ile anomali tespiti.

    Args:
        df: 'volume' kolonu iceren DataFrame
        period: Hacim ortalama periyodu (varsayilan 20)
        z_threshold: Z-skor esigi (varsayilan 3.0)
        min_volume_ratio: Minimum hacim/ortalama orani

    Returns:
        df: 'Vol_ZScore', 'Volume_Anomaly' kolonlari eklenmis
    """
    df = df.copy()
    df["Vol_MA"] = df["volume"].rolling(window=period).mean()
    df["Vol_Std"] = df["volume"].rolling(window=period).std()
    df["Vol_ZScore"] = (df["volume"] - df["Vol_MA"]) / df["Vol_Std"].replace(0, np.nan)
    df["Volume_Ratio"] = df["volume"] / df["Vol_MA"]

    df["Volume_Anomaly"] = (
        (df["Vol_ZScore"] > z_threshold) &
        (df["Volume_Ratio"] > min_volume_ratio)
    )

    return df


def summarize_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Anomali gunlerini ozet tabloya donusturur."""
    anomalies = df[df["Volume_Anomaly"] == True].copy()
    if anomalies.empty:
        return pd.DataFrame()

    anomalies["Anomaly_Strength"] = pd.cut(
        anomalies["Vol_ZScore"],
        bins=[0, 3, 5, 10, np.inf],
        labels=["Z>3", "Z>5", "Z>10", "Z>10+"],
    )
    return anomalies[["close", "volume", "Vol_ZScore", "Volume_Ratio", "Anomaly_Strength"]]
