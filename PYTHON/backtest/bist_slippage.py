"""
bist_slippage.py — Advanced BIST Slippage Model
K155-K158: Tick-size spread, session-based slippage, mid-point impact, depth-based.
Inherits from SlippageModel.
"""

import math
from datetime import time
from typing import Optional
from .slippage import SlippageModel


class BISTSlippageModel(SlippageModel):
    """
    BIST piyasasına özel slippage modeli.
    """

    # BIST tick size kuralları (örnek)
    TICK_SIZE_RULES = [
        (0.0, 9.99, 0.01),
        (10.0, 49.99, 0.02),
        (50.0, 99.99, 0.05),
        (100.0, float("inf"), 0.10),
    ]

    # Seans bazlı çarpanlar
    SESSION_MULTIPLIERS = {
        "opening": 2.5,   # 09:30-09:45
        "continuous": 1.0,  # 09:45-17:45
        "closing": 1.5,     # 17:45-18:00
    }

    def __init__(
        self,
        base_rate: float = 0.001,
        max_rate: float = 0.01,
        spread_factor: float = 5.0,
        midpoint_threshold_value: float = 100_000.0,  # TL
        depth_threshold: int = 5,
    ):
        super().__init__(base_rate, max_rate, spread_factor)
        self.midpoint_threshold_value = midpoint_threshold_value
        self.depth_threshold = depth_threshold

    def get_tick_size(self, price: float) -> float:
        """Fiyata göre BIST tick size'ı."""
        for low, high, tick in self.TICK_SIZE_RULES:
            if low <= price <= high:
                return tick
        return 0.01

    def _get_session_multiplier(self, session_time) -> float:
        """
        Zaman dilimine göre slippage çarpanı.
        session_time: datetime.time veya string "HH:MM"
        """
        if isinstance(session_time, str):
            hour, minute = map(int, session_time.split(":"))
            t = time(hour, minute)
        else:
            t = session_time

        if time(9, 30) <= t < time(9, 45):
            return self.SESSION_MULTIPLIERS["opening"]
        elif time(9, 45) <= t < time(17, 45):
            return self.SESSION_MULTIPLIERS["continuous"]
        elif time(17, 45) <= t <= time(18, 0):
            return self.SESSION_MULTIPLIERS["closing"]
        return 1.0

    def calculate(
        self,
        order_value: float,
        avg_daily_volume: float,
        price: float,
        session_time=None,
        order_book_depth: int = 10,
    ) -> float:
        """
        BIST özel slippage hesaplama.
        """
        # Temel slippage (SlippageModel'den)
        base_slippage = super().calculate(order_value, avg_daily_volume, price)

        # Tick size minimum spread
        tick = self.get_tick_size(price)
        min_spread = tick / price if price > 0 else 0.0

        # Seans çarpanı
        session_mult = self._get_session_multiplier(session_time) if session_time else 1.0

        # Derinlik çarpanı
        depth_mult = 1.5 if order_book_depth < self.depth_threshold else 1.0

        # Mid-point etkisi (büyük emirlerde slippage düşer)
        midpoint_discount = 1.0
        if order_value >= self.midpoint_threshold_value:
            midpoint_discount = 0.7  # %30 azalma

        # Toplam slippage
        slippage = max(base_slippage, min_spread) * session_mult * depth_mult * midpoint_discount
        return min(slippage, self.max_rate)

    def apply(
        self,
        price: float,
        side: str,
        order_value: float,
        avg_daily_volume: float,
        session_time=None,
        order_book_depth: int = 10,
    ) -> float:
        """Fiyata slippage uygula."""
        rate = self.calculate(order_value, avg_daily_volume, price, session_time, order_book_depth)
        if side.upper() == "BUY":
            return price * (1 + rate)
        elif side.upper() == "SELL":
            return price * (1 - rate)
        return price
