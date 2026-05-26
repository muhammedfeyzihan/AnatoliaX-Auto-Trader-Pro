"""
commission.py — BIST islem maliyeti (Komisyon + BSMV)
K103: Islem maliyeti hesaplama
"""


class CommissionModel:
    """BIST islem maliyeti modeli.

    Varsayilan maliyetler (araci kuruma gore degisir):
    - Komisyon: %0.10 (alis) + %0.10 (satis) = %0.20 round-trip
    - BSMV (Banka ve Sigorta Muamele Vergisi): %0.10 (alis) + %0.10 (satis) = %0.20 round-trip
    - Toplam round-trip: ~%0.40
    """

    def __init__(self, commission_rate: float = 0.001, bsmv_rate: float = 0.001):
        self.commission_rate = commission_rate  # %0.1 yon basina
        self.bsmv_rate = bsmv_rate              # %0.1 yon basina

    def calculate(self, price: float, size: float) -> dict:
        """Tek yon islem maliyetini hesaplar."""
        value = price * size
        commission = value * self.commission_rate
        bsmv = value * self.bsmv_rate
        total = commission + bsmv
        return {
            "value": value,
            "commission": commission,
            "bsmv": bsmv,
            "total": total,
            "rate": self.commission_rate + self.bsmv_rate,
        }

    def round_trip(self, entry_price: float, exit_price: float, size: float) -> dict:
        """Alis + satis toplam maliyetini hesaplar."""
        buy = self.calculate(entry_price, size)
        sell = self.calculate(exit_price, size)
        gross_profit = (exit_price - entry_price) * size
        net_profit = gross_profit - buy["total"] - sell["total"]
        return {
            "buy_cost": buy["total"],
            "sell_cost": sell["total"],
            "total_cost": buy["total"] + sell["total"],
            "gross_profit": gross_profit,
            "net_profit": net_profit,
            "net_return": net_profit / (entry_price * size) if entry_price > 0 else 0,
        }

    def net_tp(self, entry_price: float, gross_tp_pct: float, size: float = 1.0) -> float:
        """Brut TP'den net TP fiyatini hesaplar."""
        gross_tp = entry_price * (1 + gross_tp_pct)
        rt = self.round_trip(entry_price, gross_tp, size)
        net_return = rt["net_return"]
        return entry_price * (1 + net_return)


def apply_commission_to_trades(trades, model: CommissionModel = None) -> pd.DataFrame:
    """Trades DataFrame'ine komisyon ve net kar uygular."""
    import pandas as pd
    if model is None:
        model = CommissionModel()

    results = []
    for _, row in trades.iterrows():
        rt = model.round_trip(row["entry_price"], row["exit_price"], row["size"])
        results.append(rt)

    cost_df = pd.DataFrame(results)
    trades = trades.copy()
    for col in cost_df.columns:
        trades[f"comm_{col}"] = cost_df[col].values
    return trades
