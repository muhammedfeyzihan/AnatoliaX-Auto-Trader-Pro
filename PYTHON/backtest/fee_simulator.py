"""
fee_simulator.py — Realistic BIST Fee Simulation
K189-K192: BIST fee, Takasbank fee, tiered brokerage, BSMV.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class FeeBreakdown:
    bist_fee: float
    takasbank_fee: float
    brokerage_commission: float
    bsmv: float
    total: float


class RealisticFeeSimulator:
    """
    BIST işlem maliyetlerini gerçekçi şekilde simüle eden motor.
    """

    # BIST işlem ücreti (yaklaşık, her yön)
    BIST_FEE_RATE = 0.000035  # %0.0035

    # Takasbank ücreti (yaklaşık, her yön)
    TAKASBANK_FEE_RATE = 0.00001  # %0.001

    # BSMV (Banka ve Sigorta Muamele Vergisi)
    BSMV_RATE = 0.001  # %0.10 her yön

    # Aracı kurum komisyonu tier'ları (aylık hacme göre)
    BROKERAGE_TIERS = [
        (0, 50_000, 0.0015),       # < 50K TL → %0.15
        (50_000, 250_000, 0.0012),  # 50K-250K → %0.12
        (250_000, float("inf"), 0.0010),  # > 250K → %0.10
    ]

    def __init__(
        self,
        bist_fee_rate: float = None,
        takasbank_fee_rate: float = None,
        bsmv_rate: float = None,
        brokerage_tiers=None,
    ):
        self.bist_fee_rate = bist_fee_rate if bist_fee_rate is not None else self.BIST_FEE_RATE
        self.takasbank_fee_rate = takasbank_fee_rate if takasbank_fee_rate is not None else self.TAKASBANK_FEE_RATE
        self.bsmv_rate = bsmv_rate if bsmv_rate is not None else self.BSMV_RATE
        self.brokerage_tiers = brokerage_tiers if brokerage_tiers is not None else self.BROKERAGE_TIERS

    def _brokerage_rate(self, monthly_volume_tlt: float) -> float:
        """Aylık hacme göre aracı kurum komisyon oranı."""
        for low, high, rate in self.brokerage_tiers:
            if low <= monthly_volume_tlt < high:
                return rate
        return self.brokerage_tiers[-1][2]

    def calculate(self, price: float, size: float, monthly_volume_tlt: float = 0.0) -> FeeBreakdown:
        """
        Tek yön işlem maliyetini hesaplar.
        """
        value = price * size
        bist_fee = value * self.bist_fee_rate
        takasbank_fee = value * self.takasbank_fee_rate
        brokerage_rate = self._brokerage_rate(monthly_volume_tlt)
        brokerage_commission = value * brokerage_rate
        bsmv = value * self.bsmv_rate
        total = bist_fee + takasbank_fee + brokerage_commission + bsmv
        return FeeBreakdown(
            bist_fee=bist_fee,
            takasbank_fee=takasbank_fee,
            brokerage_commission=brokerage_commission,
            bsmv=bsmv,
            total=total,
        )

    def round_trip(
        self,
        entry_price: float,
        exit_price: float,
        size: float,
        monthly_volume_tlt: float = 0.0,
    ) -> dict:
        """
        Alış + satış toplam maliyetini hesaplar.
        """
        buy = self.calculate(entry_price, size, monthly_volume_tlt)
        sell = self.calculate(exit_price, size, monthly_volume_tlt)
        gross_profit = (exit_price - entry_price) * size
        total_cost = buy.total + sell.total
        net_profit = gross_profit - total_cost
        return {
            "entry_price": entry_price,
            "exit_price": exit_price,
            "size": size,
            "buy": {
                "bist_fee": buy.bist_fee,
                "takasbank_fee": buy.takasbank_fee,
                "brokerage_commission": buy.brokerage_commission,
                "bsmv": buy.bsmv,
                "total": buy.total,
            },
            "sell": {
                "bist_fee": sell.bist_fee,
                "takasbank_fee": sell.takasbank_fee,
                "brokerage_commission": sell.brokerage_commission,
                "bsmv": sell.bsmv,
                "total": sell.total,
            },
            "total_cost": total_cost,
            "gross_profit": gross_profit,
            "net_profit": net_profit,
            "net_return": net_profit / (entry_price * size) if entry_price > 0 else 0.0,
        }

    def estimate_total_round_trip_rate(self, monthly_volume_tlt: float = 0.0) -> float:
        """Yaklaşık toplam round-trip maliyet oranı."""
        brokerage = self._brokerage_rate(monthly_volume_tlt)
        return (self.bist_fee_rate + self.takasbank_fee_rate + brokerage + self.bsmv_rate) * 2
