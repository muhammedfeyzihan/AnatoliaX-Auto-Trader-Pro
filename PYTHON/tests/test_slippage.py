"""
Test: PYTHON.backtest.slippage
Hacme bagli slippage modeli dogrulama.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backtest.slippage import SlippageModel


class TestSlippageModel:
    def test_high_liquidity_low_slippage(self):
        slip = SlippageModel(base_rate=0.001, max_rate=0.01, spread_factor=5.0)
        rate = slip.calculate(order_value=5000, avg_daily_volume=5000000, price=50)
        # Yuksek hacimli hisse: slip dusuk olmali
        assert rate < 0.005
        assert rate >= 0.0

    def test_low_liquidity_high_slippage(self):
        slip = SlippageModel(base_rate=0.001, max_rate=0.01, spread_factor=5.0)
        rate = slip.calculate(order_value=50000, avg_daily_volume=100000, price=50)
        # Dusuk hacimli hisse: slip yuksek olmali
        assert rate > 0.001
        assert rate <= 0.01

    def test_max_rate_cap(self):
        slip = SlippageModel(base_rate=0.001, max_rate=0.01, spread_factor=5.0)
        rate = slip.calculate(order_value=500000, avg_daily_volume=10000, price=50)
        # Asiri dusuk hacim: max_rate'e takilmali
        assert rate <= 0.01

    def test_base_rate_minimum(self):
        slip = SlippageModel(base_rate=0.001, max_rate=0.01, spread_factor=5.0)
        rate = slip.calculate(order_value=1, avg_daily_volume=999999999, price=50)
        # Asiri yuksek hacim: base_rate'e yaklasmali
        assert rate >= 0.001

    def test_liquidity_check(self):
        slip = SlippageModel(base_rate=0.001, max_rate=0.01, spread_factor=5.0)
        # depth = avg_daily_volume * price; order_value < depth * 0.1 -> likidite kontrolu
        # depth=50000, price=10 -> avg_daily_volume=5000; order_value=1000 < 5000 -> True
        is_liquid = slip.check_liquidity(order_value=1000, avg_daily_volume=5000, price=10)
        assert is_liquid is True

        # depth=5000, price=10 -> avg_daily_volume=500; order_value=10000 > 500 -> False
        is_not_liquid = slip.check_liquidity(order_value=10000, avg_daily_volume=500, price=10)
        assert is_not_liquid is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
