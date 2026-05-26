"""
execution/iceberg_detector.py — Gizli likidite tespiti (boyut kumeleme ile)
"""
from decimal import Decimal
from typing import List


class IcebergDetector:
    """
    Gizli likidite tespiti.

    Algoritma:
    - Ayni fiyat seviyesinde tekrarlayan sabit boyutlu emirler iceberg isareti
    - Kumeleme: boyut > ortalama + 2*std olan emirler potansiyel iceberg
    - Q_effective = Q_visible + Q_hidden * detection_probability

    K151: Iceberg tespiti market maker kotasyonunu etkiler.
    """

    def __init__(self, window: int = 100, z_threshold: float = 2.0):
        self.window = window
        self.z_threshold = z_threshold
        self._sizes: List[Decimal] = []

    def on_order(self, price: Decimal, size: Decimal) -> bool:
        """Emir geldi; iceberg mi? True ise gizli likidite sinyali."""
        import statistics
        self._sizes.append(size)
        if len(self._sizes) > self.window:
            self._sizes.pop(0)
        if len(self._sizes) < 10:
            return False
        mean = statistics.mean(self._sizes)
        std = statistics.stdev(self._sizes) if len(self._sizes) > 1 else 0
        z = float(size - mean) / std if std > 0 else 0
        return z >= self.z_threshold

    def estimate_hidden(self, visible_size: Decimal) -> Decimal:
        """Gorunen boyuta gore gizli likidite tahmini."""
        return visible_size * Decimal("1.5")
