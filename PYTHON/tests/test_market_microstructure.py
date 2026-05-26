"""
test_market_microstructure.py — Market Microstructure Tests
"""

import pytest
import pandas as pd
import numpy as np
from backtest.market_microstructure import MarketMicrostructure


class TestMarketMicrostructure:
    def test_simulate_order_book(self):
        mm = MarketMicrostructure()
        ob = mm.simulate_order_book("THYAO", mid_price=100.0, avg_daily_volume=1_000_000, n_levels=5)
        assert "bids" in ob
        assert "asks" in ob
        assert len(ob["bids"]) == 5
        assert len(ob["asks"]) == 5
        assert ob["bids"][0].price < 100.0
        assert ob["asks"][0].price > 100.0

    def test_market_impact_basic(self):
        mm = MarketMicrostructure()
        impact = mm.market_impact(order_size=10_000, adv=1_000_000, volatility=0.02)
        assert impact > 0
        assert impact < 0.05

    def test_market_impact_zero_adv(self):
        mm = MarketMicrostructure()
        impact = mm.market_impact(order_size=10_000, adv=0, volatility=0.02)
        assert impact == 0.0

    def test_vwap_benchmark(self):
        mm = MarketMicrostructure()
        df = pd.DataFrame({
            "close": [100.0, 101.0, 102.0],
            "volume": [1000, 2000, 3000],
        })
        vwap = mm.vwap_benchmark(df)
        expected = (100*1000 + 101*2000 + 102*3000) / 6000
        assert vwap == pytest.approx(expected, rel=1e-6)

    def test_vwap_benchmark_missing_cols(self):
        mm = MarketMicrostructure()
        df = pd.DataFrame({"close": [100, 101]})
        assert mm.vwap_benchmark(df) == 0.0

    def test_execution_vs_vwap_buy_good(self):
        mm = MarketMicrostructure()
        df = pd.DataFrame({
            "close": [100.0, 101.0, 102.0],
            "volume": [1000, 2000, 3000],
        })
        result = mm.execution_vs_vwap(100.5, df, side="BUY")
        assert "vwap" in result
        assert "slippage_vs_vwap" in result

    def test_execution_vs_vwap_flag(self):
        mm = MarketMicrostructure()
        df = pd.DataFrame({
            "close": [100.0, 100.0, 100.0],
            "volume": [1000, 1000, 1000],
        })
        # VWAP = 100.0
        result = mm.execution_vs_vwap(100.2, df, side="BUY")
        assert result["flag"] is True
        assert "worse" in result["reason"]

    def test_bid_ask_bounce(self):
        mm = MarketMicrostructure()
        prices = pd.Series([100.0, 100.5, 100.2, 100.8])
        volumes = pd.Series([1000, 500, 800, 600])
        bounce = mm.bid_ask_bounce(prices, volumes)
        assert len(bounce) == 4
        assert bounce.iloc[0] == 0.0
