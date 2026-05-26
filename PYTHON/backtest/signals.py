"""
signals.py — Sinyal uretimi (teknik indikator kombinasyonlari)
EMA Cross, RSI Extreme, BB Squeeze + Volume, VWAP Bounce, Momentum Spike
v3.3+: SignalConfig entegrasyonu — regime-uyarlanabilir agirliklar ve esikler
"""
import pandas as pd
import numpy as np
from . import indicators
from strategy.parameter_registry import SignalConfig


def ema_cross_signal(df: pd.DataFrame) -> pd.Series:
    """EMA9 > EMA21 cross sinyali."""
    df = indicators.ema(df, periods=[9, 21])
    cross = (df["EMA9"] > df["EMA21"]) & (df["EMA9"].shift(1) <= df["EMA21"].shift(1))
    return cross.astype(int)


def rsi_extreme_signal(df: pd.DataFrame, oversold: float = 30, overbought: float = 70) -> pd.Series:
    """RSI asiri degerlerden donus sinyali."""
    df = indicators.rsi(df)
    # Oversold cikis (bullish) veya overbought donus (bearish)
    oversold_exit = (df["RSI"] > oversold) & (df["RSI"].shift(1) <= oversold)
    return oversold_exit.astype(int)


def bb_squeeze_volume_signal(df: pd.DataFrame, volume_z: float = 2.5) -> pd.Series:
    """Bollinger squeeze + hacim patlamasi kombinasyonu."""
    df = indicators.bollinger(df)
    df = indicators.volume_profile(df)
    squeeze = df["BB_Squeeze"] == True
    volume_spike = df["Vol_ZScore"] > volume_z
    return (squeeze & volume_spike).astype(int)


def vwap_bounce_signal(df: pd.DataFrame, deviation_max: float = 0.02) -> pd.Series:
    """Fiyat VWAP yakinindan yukari donus."""
    df = indicators.vwap(df)
    deviation = (df["close"] - df["VWAP"]) / df["VWAP"]
    bounce = (deviation > 0) & (deviation < deviation_max) & (df["close"] > df["close"].shift(1))
    return bounce.astype(int)


def momentum_spike_signal(df: pd.DataFrame, threshold: float = 0.02) -> pd.Series:
    """Anlik fiyat sicramasi + hacim patlamasi."""
    df = indicators.volume_profile(df)
    price_change = df["close"].pct_change()
    spike = (price_change > threshold) & (df["Vol_ZScore"] > 2.0)
    return spike.astype(int)


def combined_signal(df: pd.DataFrame, indicators_needed: list[str] | None = None, config: SignalConfig | None = None) -> pd.DataFrame:
    """
    Tum sinyalleri birlestirir (agirlikli).
    v3.3+: SignalConfig ile regime-uyarlanabilir agirliklar ve esikler.

    SIGNAL = EMA(ema_weight*100) + RSI(rsi_weight*100) + Hacim(volume_weight*100)
           + BB(bb_weight*100) + VWAP(vwap_weight*100) + MACD(macd_weight*100)
    Skor > score_strong = STRONG BUY, score_moderate-score_strong = BUY,
    score_weak-score_moderate = WAIT, < score_weak = REJECT

    indicators_needed: Sadece belirtilen indikatörleri hesapla.
        ['ema','rsi','macd','bb','vwap','volume'] — None = hepsi
    config: SignalConfig — None = default degerler
    """
    cfg = config or SignalConfig()

    # Lazy indicator computation: only compute what's needed
    needed = set(indicators_needed or ["ema", "rsi", "macd", "bb", "vwap", "volume"])

    if "ema" in needed:
        df = indicators.ema(df, periods=[9, 21])
    if "rsi" in needed:
        df = indicators.rsi(df)
    if "macd" in needed:
        df = indicators.macd(df)
    if "bb" in needed:
        df = indicators.bollinger(df)
    if "vwap" in needed:
        df = indicators.vwap(df)
    if "volume" in needed or "bb" in needed:
        df = indicators.volume_profile(df)

    scores = pd.Series(0.0, index=df.index)

    # EMA uyum (EMA9 > EMA21)
    if "ema" in needed and "EMA9" in df.columns and "EMA21" in df.columns:
        scores += (df["EMA9"] > df["EMA21"]).astype(float) * (cfg.ema_weight * 100)

    # RSI momentum (regime-adaptive thresholds)
    if "rsi" in needed and "RSI" in df.columns:
        rsi_ok = (df["RSI"] >= cfg.rsi_lower) & (df["RSI"] <= cfg.rsi_upper)
        scores += rsi_ok.astype(float) * (cfg.rsi_weight * 100)

    # Hacim patlamasi (regime-adaptive Z threshold)
    if "volume" in needed and "Vol_ZScore" in df.columns:
        scores += (df["Vol_ZScore"] > cfg.volume_z_threshold).astype(float) * (cfg.volume_weight * 100)

    # Bollinger squeeze
    if "bb" in needed and "BB_Squeeze" in df.columns:
        scores += (df["BB_Squeeze"] == True).astype(float) * (cfg.bb_weight * 100)

    # VWAP uzerinde (regime-adaptive deviation)
    if "vwap" in needed and "VWAP" in df.columns:
        vwap_ok = (df["close"] > df["VWAP"]) & ((df["close"] - df["VWAP"]) / df["VWAP"] < cfg.vwap_deviation_max)
        scores += vwap_ok.astype(float) * (cfg.vwap_weight * 100)

    # MACD histogram pozitif
    if "macd" in needed and "MACD_Hist" in df.columns:
        macd_ok = df["MACD_Hist"] > 0
        scores += macd_ok.astype(float) * (cfg.macd_weight * 100)

    df["Signal_Score"] = scores
    df["Signal"] = np.where(scores >= cfg.score_strong, 2, np.where(scores >= cfg.score_moderate, 1, 0))
    return df
