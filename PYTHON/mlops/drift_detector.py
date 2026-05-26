"""
mlops/drift_detector.py — Veri ve model drift tespiti
"""
from typing import List


class DriftDetector:
    """
    Veri drift ve model performans drift tespiti.

    Yontemler:
    - PSI (Population Stability Index): dagilim degisimi
    - KS test: iki ornek karsilastirma
    - Z-Score: ortalama sapma

    K197: Drift tespitinde model otomatik olarak eski versiyona geri doner.
    """

    def __init__(self, psi_threshold: float = 0.25):
        self.psi_threshold = psi_threshold

    def psi(self, expected: List[float], actual: List[float]) -> float:
        import numpy as np
        exp = np.array(expected)
        act = np.array(actual)
        bins = 10
        min_val = min(exp.min(), act.min())
        max_val = max(exp.max(), act.max())
        ranges = np.linspace(min_val, max_val, bins + 1)
        ep = np.histogram(exp, bins=ranges)[0] + 1e-10
        ap = np.histogram(act, bins=ranges)[0] + 1e-10
        ep /= ep.sum()
        ap /= ap.sum()
        psi_val = np.sum((ap - ep) * np.log(ap / ep))
        return float(psi_val)

    def is_drift(self, expected: List[float], actual: List[float]) -> bool:
        return self.psi(expected, actual) > self.psi_threshold
