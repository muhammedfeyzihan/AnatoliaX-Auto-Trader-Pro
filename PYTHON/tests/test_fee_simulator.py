"""
test_fee_simulator.py — Realistic Fee Simulator Tests
"""

import pytest
from backtest.fee_simulator import RealisticFeeSimulator


class TestRealisticFeeSimulator:
    def test_brokerage_rate_low_tier(self):
        sim = RealisticFeeSimulator()
        rate = sim._brokerage_rate(30_000)
        assert rate == 0.0015

    def test_brokerage_rate_mid_tier(self):
        sim = RealisticFeeSimulator()
        rate = sim._brokerage_rate(100_000)
        assert rate == 0.0012

    def test_brokerage_rate_high_tier(self):
        sim = RealisticFeeSimulator()
        rate = sim._brokerage_rate(300_000)
        assert rate == 0.0010

    def test_calculate_single_direction(self):
        sim = RealisticFeeSimulator()
        fee = sim.calculate(price=100.0, size=10, monthly_volume_tlt=0)
        value = 1000.0
        assert fee.bist_fee == value * sim.bist_fee_rate
        assert fee.takasbank_fee == value * sim.takasbank_fee_rate
        assert fee.bsmv == value * sim.bsmv_rate
        assert fee.brokerage_commission == value * 0.0015
        assert fee.total > 0

    def test_round_trip(self):
        sim = RealisticFeeSimulator()
        result = sim.round_trip(entry_price=100.0, exit_price=110.0, size=10, monthly_volume_tlt=0)
        assert result["gross_profit"] == 100.0
        assert result["total_cost"] > 0
        assert result["net_profit"] < result["gross_profit"]
        assert result["net_return"] > 0

    def test_round_trip_loss(self):
        sim = RealisticFeeSimulator()
        result = sim.round_trip(entry_price=100.0, exit_price=90.0, size=10, monthly_volume_tlt=0)
        assert result["gross_profit"] == -100.0
        assert result["net_profit"] < -100.0
        assert result["net_return"] < 0

    def test_round_trip_high_volume_tier(self):
        sim = RealisticFeeSimulator()
        result_low = sim.round_trip(entry_price=100.0, exit_price=110.0, size=10, monthly_volume_tlt=0)
        result_high = sim.round_trip(entry_price=100.0, exit_price=110.0, size=10, monthly_volume_tlt=300_000)
        assert result_high["total_cost"] < result_low["total_cost"]

    def test_estimate_total_round_trip_rate(self):
        sim = RealisticFeeSimulator()
        rate_low = sim.estimate_total_round_trip_rate(monthly_volume_tlt=0)
        rate_high = sim.estimate_total_round_trip_rate(monthly_volume_tlt=300_000)
        assert rate_high < rate_low
        assert rate_low > 0.005  # At least ~0.5%

    def test_custom_rates(self):
        sim = RealisticFeeSimulator(bist_fee_rate=0.0001, takasbank_fee_rate=0.0001, bsmv_rate=0.001)
        fee = sim.calculate(price=100.0, size=10)
        assert fee.bist_fee == 1000.0 * 0.0001
        assert fee.takasbank_fee == 1000.0 * 0.0001
        assert fee.bsmv == 1000.0 * 0.001
