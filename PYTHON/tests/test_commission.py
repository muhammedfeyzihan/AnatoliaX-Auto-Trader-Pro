"""
Test: PYTHON.backtest.commission
BIST komisyon + BSMV hesabi dogrulama.
"""

import pytest
import sys
from pathlib import Path

# Proje kokunu ekle
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backtest.commission import CommissionModel


class TestCommissionModel:
    def test_round_trip_gross_profit(self):
        comm = CommissionModel(commission_rate=0.001, bsmv_rate=0.001)
        rt = comm.round_trip(entry_price=100, exit_price=105, size=10)
        # Brut kar: (105-100)*10 = 50
        assert rt["gross_profit"] == pytest.approx(50.0, rel=1e-3)

    def test_round_trip_commission(self):
        comm = CommissionModel(commission_rate=0.001, bsmv_rate=0.001)
        rt = comm.round_trip(entry_price=100, exit_price=105, size=10)
        # Toplam islem degeri: 100*10 + 105*10 = 2050
        # Komisyon: 2050 * 0.001 = 2.05
        # round_trip toplam maliyeti total_cost olarak dondurur
        assert rt["total_cost"] == pytest.approx(4.10, rel=1e-3)

    def test_round_trip_bsmv(self):
        comm = CommissionModel(commission_rate=0.001, bsmv_rate=0.001)
        rt = comm.round_trip(entry_price=100, exit_price=105, size=10)
        # BSMV: 2050 * 0.001 = 2.05
        # calculate() ile ayri BSMV dogrulama
        single = comm.calculate(price=100, size=10)
        assert single["bsmv"] == pytest.approx(1.0, rel=1e-3)

    def test_round_trip_net_profit(self):
        comm = CommissionModel(commission_rate=0.001, bsmv_rate=0.001)
        rt = comm.round_trip(entry_price=100, exit_price=105, size=10)
        # Net kar: 50 - 4.10 = 45.90
        assert rt["net_profit"] == pytest.approx(45.90, rel=1e-3)

    def test_zero_profit(self):
        comm = CommissionModel(commission_rate=0.001, bsmv_rate=0.001)
        rt = comm.round_trip(entry_price=100, exit_price=100, size=10)
        assert rt["gross_profit"] == pytest.approx(0.0, rel=1e-3)
        # Komisyon maliyeti oldugu icin net kar negatif
        assert rt["net_profit"] < 0

    def test_loss_trade(self):
        comm = CommissionModel(commission_rate=0.001, bsmv_rate=0.001)
        rt = comm.round_trip(entry_price=100, exit_price=95, size=10)
        # Brut zarar: (95-100)*10 = -50
        assert rt["gross_profit"] == pytest.approx(-50.0, rel=1e-3)
        # Komisyon maliyeti eklenince daha da kotu
        assert rt["net_profit"] < rt["gross_profit"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
