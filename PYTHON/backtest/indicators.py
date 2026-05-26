"""
indicators.py — Teknik indikatörler (Pandas/NumPy vektörize)
EMA, RSI, MACD, Bollinger Bands, VWAP, ATR, Hacim Ort.
"""
import pandas as pd
import numpy as np


def ema(df: pd.DataFrame, col: str = "close", periods: list = None) -> pd.DataFrame:
    """Coklu EMA hesaplar. Varsayilan: 9, 21, 50."""
    if periods is None:
        periods = [9, 21, 50]
    for p in periods:
        df[f"EMA{p}"] = df[col].ewm(span=p, adjust=False).mean()
    return df


def rsi(df: pd.DataFrame, col: str = "close", period: int = 14) -> pd.DataFrame:
    """RSI hesaplar."""
    delta = df[col].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))
    return df


def macd(df: pd.DataFrame, col: str = "close", fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """MACD histogram hesaplar."""
    ema_fast = df[col].ewm(span=fast, adjust=False).mean()
    ema_slow = df[col].ewm(span=slow, adjust=False).mean()
    df["MACD"] = ema_fast - ema_slow
    df["MACD_Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]
    return df


def bollinger(df: pd.DataFrame, col: str = "close", period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
    """Bollinger Bandlari hesaplar."""
    sma = df[col].rolling(window=period).mean()
    std = df[col].rolling(window=period).std()
    df["BB_Middle"] = sma
    df["BB_Upper"] = sma + (std * std_dev)
    df["BB_Lower"] = sma - (std * std_dev)
    df["BB_Width"] = (df["BB_Upper"] - df["BB_Lower"]) / df["BB_Middle"]
    df["BB_Squeeze"] = df["BB_Width"] < 0.05
    return df


def vwap(df: pd.DataFrame) -> pd.DataFrame:
    """VWAP (Volume Weighted Average Price) hesaplar. Gunluk."""
    df["VWAP"] = (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum()
    return df


def atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Average True Range hesaplar."""
    high_low = df["high"] - df["low"]
    high_close = np.abs(df["high"] - df["close"].shift())
    low_close = np.abs(df["low"] - df["close"].shift())
    # np.maximum avoids intermediate DataFrame allocation (K97)
    tr = np.maximum(np.maximum(high_low, high_close), low_close)
    df["ATR"] = tr.rolling(window=period).mean()
    return df


def volume_profile(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Hacim ortalamasi ve Z-skorunu hesaplar."""
    df["Vol_MA"] = df["volume"].rolling(window=period).mean()
    df["Vol_Std"] = df["volume"].rolling(window=period).std()
    df["Vol_ZScore"] = (df["volume"] - df["Vol_MA"]) / df["Vol_Std"].replace(0, np.nan)
    return df


def apply_all(df: pd.DataFrame) -> pd.DataFrame:
    """Tum indikatörleri uygular."""
    df = ema(df)
    df = rsi(df)
    df = macd(df)
    df = bollinger(df)
    df = vwap(df)
    df = atr(df)
    df = volume_profile(df)
    return df
