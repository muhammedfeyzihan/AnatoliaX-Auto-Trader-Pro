"""
portfolio_heat.py — Portfoy sicakligi, korelasyon riski, liquidation distance
"""
import numpy as np
import pandas as pd
from typing import Dict, List


class PortfolioHeat:
    """
    Portfoy risk yogunlugu:
    - Heat = toplam risk / sermaye
    - Korelasyon agirlikli risk
    - Likidasyon mesafesi (her pozisyon icin % kac duserse margin call)
    """

    def __init__(self, max_heat: float = 0.25):
        self.max_heat = max_heat

    def calculate_heat(self, positions: List[dict], capital: float) -> dict:
        total_risk = 0.0
        for p in positions:
            sl = p.get("stop_loss", p.get("entry_price", 0) * 0.95)
            entry = p.get("entry_price", 0)
            size = p.get("size", 0)
            risk_per_share = abs(entry - sl) if entry and sl else 0
            total_risk += risk_per_share * size

        heat = total_risk / capital if capital > 0 else 0
        return {
            "heat": round(heat, 4),
            "max_heat": self.max_heat,
            "total_risk": round(total_risk, 2),
            "allowed": heat < self.max_heat,
        }

    def correlation_risk(self, returns_df: pd.DataFrame, weights: np.ndarray = None) -> dict:
        """Korelasyon matrisi ve ortalama korelasyon."""
        if returns_df.empty or len(returns_df.columns) < 2:
            return {"avg_correlation": 0.0, "max_correlation": 0.0, "alerts": []}

        corr = returns_df.corr()
        triu = np.triu(corr.values, k=1)
        vals = triu[triu != 0]
        avg_corr = np.mean(vals) if len(vals) > 0 else 0.0
        max_corr = np.max(vals) if len(vals) > 0 else 0.0

        alerts = []
        if max_corr > 0.80:
            # Hangi cift
            for i in range(len(corr.columns)):
                for j in range(i + 1, len(corr.columns)):
                    if corr.iloc[i, j] > 0.80:
                        alerts.append(f"HIGH_CORR: {corr.columns[i]} - {corr.columns[j]} {corr.iloc[i,j]:.2f}")

        return {
            "avg_correlation": round(avg_corr, 3),
            "max_correlation": round(max_corr, 3),
            "alerts": alerts,
        }

    def liquidation_distance(self, positions: List[dict], capital: float) -> List[dict]:
        """Her pozisyon icin sermayenin %kacina dustugunde margin call."""
        results = []
        for p in positions:
            entry = p.get("entry_price", 0)
            size = p.get("size", 0)
            value = entry * size
            if value <= 0:
                continue
            # Basit model: pozisyon degeri kadar sermaye kaybi = %100 distance
            distance_pct = capital / value if value > 0 else 0
            results.append({
                "symbol": p["symbol"],
                "value": value,
                "liquidation_distance_pct": round(distance_pct * 100, 2),
            })
        return results
