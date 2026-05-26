"""
test_bist_slippage.py — BIST Slippage Model Tests
"""

import pytest
from datetime import time
from backtest.bist_slippage import BISTSlippageModel


class TestBISTSlippageModel:
    def test_tick_size_low_price(self):
        model = BISTSlippageModel()
        assert model.get_tick_size(5.0) == 0.01
        assert model.get_tick_size(9.99) == 0.01

    def test_tick_size_mid_price(self):
        model = BISTSlippageModel()
        assert model.get_tick_size(10.0) == 0.02
        assert model.get_tick_size(49.99) == 0.02

    def test_tick_size_high_price(self):
        model = BISTSlippageModel()
        assert model.get_tick_size(50.0) == 0.05
        assert model.get_tick_size(99.99) == 0.05

    def test_tick_size_very_high_price(self):
        model = BISTSlippageModel()
        assert model.get_tick_size(100.0) == 0.10
        assert model.get_tick_size(500.0) == 0.10

    def test_session_multiplier_opening(self):
        model = BISTSlippageModel()
        assert model._get_session_multiplier(time(9, 30)) == 2.5
        assert model._get_session_multiplier(time(9, 44)) == 2.5

    def test_session_multiplier_continuous(self):
        model = BISTSlippageModel()
        assert model._get_session_multiplier(time(9, 45)) == 1.0
        assert model._get_session_multiplier(time(14, 0)) == 1.0
        assert model._get_session_multiplier(time(17, 44)) == 1.0

    def test_session_multiplier_closing(self):
        model = BISTSlippageModel()
        assert model._get_session_multiplier(time(17, 45)) == 1.5
        assert model._get_session_multiplier(time(18, 0)) == 1.5

    def test_session_multiplier_string(self):
        model = BISTSlippageModel()
        assert model._get_session_multiplier("09:30") == 2.5
        assert model._get_session_multiplier("14:00") == 1.0

    def test_calculate_with_session_and_depth(self):
        model = BISTSlippageModel(base_rate=0.001)
        slip = model.calculate(
            order_value=10_000,
            avg_daily_volume=1_000_000,
            price=100.0,
            session_time=time(9, 30),
            order_book_depth=3,
        )
        # Opening multiplier 2.5, depth multiplier 1.5, tick 0.10/100 = 0.001
        assert slip > 0.001
        assert slip <= model.max_rate

    def test_midpoint_discount(self):
        # Same large order with vs without discount threshold
        model_with_discount = BISTSlippageModel(base_rate=0.001, midpoint_threshold_value=50_000)
        model_no_discount = BISTSlippageModel(base_rate=0.001, midpoint_threshold_value=500_000)
        slip_discounted = model_with_discount.calculate(
            order_value=100_000,
            avg_daily_volume=1_000_000,
            price=100.0,
            session_time=time(14, 0),
            order_book_depth=20,
        )
        slip_full = model_no_discount.calculate(
            order_value=100_000,
            avg_daily_volume=1_000_000,
            price=100.0,
            session_time=time(14, 0),
            order_book_depth=20,
        )
        assert slip_discounted < slip_full

    def test_apply_buy(self):
        model = BISTSlippageModel(base_rate=0.001)
        price = model.apply(price=100.0, side="BUY", order_value=1_000, avg_daily_volume=1_000_000)
        assert price >= 100.0

    def test_apply_sell(self):
        model = BISTSlippageModel(base_rate=0.001)
        price = model.apply(price=100.0, side="SELL", order_value=1_000, avg_daily_volume=1_000_000)
        assert price <= 100.0
