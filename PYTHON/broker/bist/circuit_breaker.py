"""
bist/circuit_breaker.py — BIST devre kesici (A/B/C gruplari)
"""
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class CircuitBreakerLevel:
    group: str
    up_limit: float
    down_limit: float
    duration_min: int


class BISTCircuitBreaker:
    """
    BIST devre kesici sistemi.

    Gruplar:
    - A Grubu (yuksek oynaklik): ust limit %10, alt limit %10, 30 dk
    - B Grubu (orta oynaklik): ust limit %6, alt limit %6, 30 dk
    - C Grubu (dusuk oynaklik): ust limit %4, alt limit %4, 30 dk

    Tetikleyiciler:
    - Fiyat, gunluk baz fiyat + esik degerini gecerse devre kesici calisir
    - Iki tarafli (yukari ve asagi)

    Cozum:
    - Devre kesici suresi sonunda tek fiyat ile acilis (BIST uygulamasi)
    """

    LEVELS: Dict[str, CircuitBreakerLevel] = {
        "A": CircuitBreakerLevel("A", 0.10, -0.10, 30),
        "B": CircuitBreakerLevel("B", 0.06, -0.06, 30),
        "C": CircuitBreakerLevel("C", 0.04, -0.04, 30),
    }

    def __init__(self):
        self._triggered: Dict[str, bool] = {}

    def is_triggered(self, symbol: str) -> bool:
        """Sembol icin devre kesici aktif mi?"""
        return self._triggered.get(symbol, False)

    def check(self, symbol: str, group: str, base_price: float, current_price: float) -> bool:
        """Fiyat hareketini kontrol et; devre kesici tetiklenirse True dondur."""
        level = self.LEVELS.get(group)
        if not level:
            return False
        change = (current_price - base_price) / base_price
        if change >= level.up_limit or change <= level.down_limit:
            self._triggered[symbol] = True
            return True
        return False

    def reset(self, symbol: str) -> None:
        """Suresi dolunca devre kesiciyi sifirla."""
        self._triggered[symbol] = False
