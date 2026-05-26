"""
market_microstructure.py — Market Microstructure Simulator
K167-K170: Order book depth, bid-ask bounce, square-root impact, VWAP benchmark.
"""

import numpy as np
import pandas as pd
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class OrderBookLevel:
    price: float
    size: float


class MarketMicrostructure:
    """
    Emir defteri derinliği ve piyasa etkisi simülasyonu.
    """

    def __init__(self, gamma: float = 0.5):
        self.gamma = gamma  # Square-root law coefficient

    # ── Sentetik L2 Order Book (K167) ──────────────────────

    def simulate_order_book(
        self,
        symbol: str,
        mid_price: float,
        avg_daily_volume: float,
        n_levels: int = 5,
    ) -> Dict[str, List[OrderBookLevel]]:
        """
        Sentetik L2 emir defteri oluştur.
        """
        tick = self._tick_size(mid_price)
        depth_per_level = avg_daily_volume / n_levels * 0.02  # %2 of ADV per level

        bids = []
        asks = []
        for i in range(1, n_levels + 1):
            bid_price = round(mid_price - i * tick, 4)
            ask_price = round(mid_price + i * tick, 4)
            # Randomize size slightly
            bid_size = depth_per_level * (1 + np.random.normal(0, 0.1))
            ask_size = depth_per_level * (1 + np.random.normal(0, 0.1))
            bids.append(OrderBookLevel(price=bid_price, size=max(1, bid_size)))
            asks.append(OrderBookLevel(price=ask_price, size=max(1, ask_size)))

        return {"bids": bids, "asks": asks}

    def _tick_size(self, price: float) -> float:
        """BIST tick size kuralları."""
        if price < 10.0:
            return 0.01
        elif price < 50.0:
            return 0.02
        elif price < 100.0:
            return 0.05
        return 0.10

    # ── Bid-Ask Bounce (K168) ─────────────────────────────

    def bid_ask_bounce(self, prices: pd.Series, volumes: pd.Series) -> pd.Series:
        """
        Düşük hacimli hisselerde bid-ask bounce etkisi.
        Bounce = (high - low) / close * (1 / log(volume))
        """
        bounce = ((prices - prices.shift(1)).abs() / prices.shift(1).abs()) * (
            1.0 / (np.log(volumes + 1))
        )
        return bounce.fillna(0)

    # ── Square-Root Law Market Impact (K169) ──────────────

    def market_impact(
        self,
        order_size: float,
        adv: float,  # average daily volume (shares)
        volatility: float,  # daily volatility (decimal)
    ) -> float:
        """
        Square-root law: impact = γ × σ × √(order_size / ADV)
        """
        if adv <= 0 or volatility <= 0:
            return 0.0
        participation = order_size / adv
        impact = self.gamma * volatility * np.sqrt(participation)
        return impact

    # ── VWAP Benchmark (K170) ─────────────────────────────

    def vwap_benchmark(self, df: pd.DataFrame) -> float:
        """
        DataFrame'ten VWAP hesapla.
        """
        if "volume" not in df.columns or "close" not in df.columns:
            return 0.0
        total_value = (df["close"] * df["volume"]).sum()
        total_volume = df["volume"].sum()
        return total_value / total_volume if total_volume > 0 else 0.0

    def execution_vs_vwap(
        self,
        execution_price: float,
        df: pd.DataFrame,
        side: str = "BUY",
    ) -> dict:
        """
        Execution fiyatını VWAP ile karşılaştır.
        BUY: execution < VWAP → iyi
        SELL: execution > VWAP → iyi
        """
        vwap = self.vwap_benchmark(df)
        if vwap <= 0:
            return {"vwap": vwap, "slippage_vs_vwap": None, "flag": False}

        if side.upper() == "BUY":
            slippage = (execution_price - vwap) / vwap
            flag = bool(slippage > 0.001)  # More than 0.1% worse than VWAP
        else:
            slippage = (vwap - execution_price) / vwap
            flag = bool(slippage > 0.001)

        return {
            "vwap": round(vwap, 4),
            "slippage_vs_vwap": round(slippage, 6),
            "flag": flag,
            "reason": "Execution worse than VWAP" if flag else "Execution OK vs VWAP",
        }
