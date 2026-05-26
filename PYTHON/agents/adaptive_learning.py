"""
adaptive_learning.py — Adaptive Online Learning Engine
K175-K178: Incremental learning, concept drift detection, PnL-driven feature importance.
"""

import statistics
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class FeatureWeight:
    name: str
    weight: float = 1.0
    profitable_count: int = 0
    unprofitable_count: int = 0


class AdaptiveLearner:
    """
    Incremental online learning with concept drift detection.
    Falls back to simple per-feature weighting if river is not available.
    """

    def __init__(self, features: List[str], drift_threshold: float = 0.05, learning_rate: float = 0.01):
        self.features = features
        self.drift_threshold = drift_threshold
        self.learning_rate = learning_rate
        self._weights: Dict[str, FeatureWeight] = {f: FeatureWeight(f) for f in features}
        self._pnl_history: List[float] = []
        self._drift_detected = False
        self._samples_since_drift = 0
        self._model_ready = False

        # Pure-Python fallback: online linear regression (SGD)
        self._coef: Dict[str, float] = {f: 0.0 for f in features}
        self._intercept: float = 0.0
        self._sample_count: int = 0

        # Try to use river for true incremental learning
        self._river = None
        try:
            from river import linear_model, preprocessing, compose
            self._river_model = compose.Pipeline(
                preprocessing.StandardScaler(),
                linear_model.LinearRegression(optimizer="SGD", loss="square"),
            )
            self._river = True
        except ImportError:
            self._river = None

    # ── Incremental Learning (K175) ────────────────────────

    def fit_incremental(self, X: Dict[str, float], y: float, sample_weight: float = 1.0) -> None:
        """
        Tek örnek ile modeli güncelle.
        X: {feature_name: value} dict
        y: target (e.g., next return)
        """
        if self._river:
            self._river_model.learn_one(X, y)
            self._model_ready = True
            return

        # Pure-Python fallback: online SGD linear regression
        pred = sum(self._coef.get(k, 0.0) * v for k, v in X.items()) + self._intercept
        error = (y - pred) * sample_weight
        lr = self.learning_rate / (1 + self._sample_count * 0.0001)  # decay
        for k, v in X.items():
            if k in self._coef:
                self._coef[k] += lr * error * v
        self._intercept += lr * error
        self._sample_count += 1
        self._model_ready = True

    def predict(self, X: Dict[str, float]) -> Optional[float]:
        """Tahmin yap."""
        if not self._model_ready:
            return None
        if self._river:
            return self._river_model.predict_one(X)
        # Pure-Python fallback prediction
        return sum(self._coef.get(k, 0.0) * v for k, v in X.items()) + self._intercept

    # ── Concept Drift Detection (K176) ─────────────────────

    def detect_drift(self, recent_pnl_window: List[float]) -> bool:
        """
        ADWIN benzeri basit drift tespiti:
        Son N işlemin P&L ortalaması ile önceki N işlemin ortalaması arasındaki
        fark threshold'u aşıyor mu?
        """
        if len(recent_pnl_window) < 20:
            return False

        mid = len(recent_pnl_window) // 2
        first_half = recent_pnl_window[:mid]
        second_half = recent_pnl_window[mid:]

        if not first_half or not second_half:
            return False

        mean_first = statistics.mean(first_half)
        mean_second = statistics.mean(second_half)
        diff = abs(mean_second - mean_first)

        drift = diff > self.drift_threshold
        if drift:
            self._drift_detected = True
            self._samples_since_drift = 0
        else:
            self._samples_since_drift += len(second_half)

        return drift

    def is_drift_active(self) -> bool:
        """Drift tespit edildikten sonra 100 örnek bekle."""
        return self._drift_detected and self._samples_since_drift < 100

    # ── PnL-Driven Feature Importance (K177) ───────────────

    def update_feature_importance(self, X: Dict[str, float], pnl: float) -> None:
        """
        Her feature'ın kazançlı/zararlı işlemlere katkısını izle.
        """
        for name, value in X.items():
            if name not in self._weights:
                continue
            fw = self._weights[name]
            if pnl > 0:
                fw.profitable_count += 1
            else:
                fw.unprofitable_count += 1
            total = fw.profitable_count + fw.unprofitable_count
            if total > 0:
                fw.weight = fw.profitable_count / total

    def feature_importance(self) -> Dict[str, float]:
        """Feature ağırlıklarını döner."""
        return {name: fw.weight for name, fw in self._weights.items()}

    def get_top_features(self, n: int = 5) -> List[str]:
        """En önemli N feature'ı döner."""
        sorted_features = sorted(self._weights.values(), key=lambda x: x.weight, reverse=True)
        return [f.name for f in sorted_features[:n]]

    # ── Reset on Drift (K178) ──────────────────────────────

    def reset_model(self) -> None:
        """Drift tespit edilirse model sıfırla."""
        self._weights = {f: FeatureWeight(f) for f in self.features}
        self._pnl_history.clear()
        self._drift_detected = False
        self._samples_since_drift = 0
        self._model_ready = False
        self._coef = {f: 0.0 for f in self.features}
        self._intercept = 0.0
        self._sample_count = 0
        if self._river:
            try:
                from river import linear_model, preprocessing, compose
                self._river_model = compose.Pipeline(
                    preprocessing.StandardScaler(),
                    linear_model.LinearRegression(optimizer="SGD", loss="square"),
                )
            except ImportError:
                pass
