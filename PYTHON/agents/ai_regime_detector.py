"""
ai_regime_detector.py — ML-based market regime classification.
K227: AIRegimeDetector.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd


@dataclass
class RegimeResult:
    regime: str = "unknown"
    confidence: float = 0.0
    features: Dict[str, float] = None
    probabilities: Dict[str, float] = None

    def __post_init__(self):
        if self.features is None:
            self.features = {}
        if self.probabilities is None:
            self.probabilities = {}


class AIRegimeDetector:
    """
    Piyasa rejimi tespiti: trend, volatilite, momentum bazli.
    Basit ML: k-means + feature thresholds. sklearn opsiyonel.
    """

    REGIMES = ["bull", "bear", "sideways", "volatile", "low_vol"]

    def __init__(self, lookback: int = 50, n_clusters: int = 3):
        self.lookback = lookback
        self.n_clusters = n_clusters
        self._centroids: Optional[np.ndarray] = None
        self._history: List[RegimeResult] = []

    def fit(self, df: pd.DataFrame):
        """Tarihsel veriyle k-means fit et."""
        features = self._extract_features(df)
        if len(features) < self.n_clusters:
            return
        try:
            from sklearn.cluster import KMeans
            X = np.array(features).reshape(-1, 1)
            km = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
            km.fit(X)
            self._centroids = km.cluster_centers_.flatten()
        except ImportError:
            # Pure-python k-means fallback (1D)
            self._centroids = self._kmeans_fallback(np.array(features))

    def predict(self, df: pd.DataFrame) -> RegimeResult:
        """Son donem icin rejim tahmini."""
        sub = df.iloc[-self.lookback:].copy() if len(df) > self.lookback else df.copy()
        if len(sub) < 10:
            return RegimeResult(regime="unknown", confidence=0.0)

        returns = sub["close"].pct_change().dropna()
        trend = (sub["close"].iloc[-1] - sub["close"].iloc[0]) / sub["close"].iloc[0]
        vol = returns.std() * np.sqrt(252) if len(returns) > 0 else 0
        momentum = returns.mean() * 252 if len(returns) > 0 else 0

        features = {"trend": trend, "volatility": vol, "momentum": momentum}

        regime, confidence = self._classify(trend, vol, momentum)
        result = RegimeResult(
            regime=regime,
            confidence=confidence,
            features=features,
            probabilities=self._probs(trend, vol, momentum),
        )
        self._history.append(result)
        return result

    def _extract_features(self, df: pd.DataFrame) -> List[float]:
        feats = []
        for i in range(len(df) - self.lookback + 1):
            sub = df.iloc[i:i + self.lookback]
            trend = (sub["close"].iloc[-1] - sub["close"].iloc[0]) / sub["close"].iloc[0]
            feats.append(trend)
        return feats

    def _kmeans_fallback(self, data: np.ndarray) -> np.ndarray:
        # Simple 1D k-means with sorted split
        data = np.sort(data)
        step = len(data) // self.n_clusters
        return np.array([data[i * step:(i + 1) * step].mean() for i in range(self.n_clusters)])

    def _classify(self, trend: float, vol: float, momentum: float) -> tuple:
        if vol > 0.50:
            return "volatile", 0.8
        if vol < 0.10:
            return "low_vol", 0.7
        if trend > 0.15 and momentum > 0.10:
            return "bull", min(0.95, 0.7 + abs(trend))
        if trend < -0.10 and momentum < -0.05:
            return "bear", min(0.95, 0.7 + abs(trend))
        return "sideways", 0.6

    def _probs(self, trend: float, vol: float, momentum: float) -> Dict[str, float]:
        r, c = self._classify(trend, vol, momentum)
        probs = {reg: 0.05 for reg in self.REGIMES}
        probs[r] = c
        for reg in self.REGIMES:
            if reg != r:
                probs[reg] = (1 - c) / (len(self.REGIMES) - 1)
        return probs

    def get_regime_history(self) -> List[str]:
        return [r.regime for r in self._history]

    def get_summary(self) -> Dict:
        if not self._history:
            return {}
        counts = {}
        for r in self._history:
            counts[r.regime] = counts.get(r.regime, 0) + 1
        total = len(self._history)
        return {reg: cnt / total for reg, cnt in counts.items()}
