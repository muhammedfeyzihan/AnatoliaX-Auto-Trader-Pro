"""
slippage.py — Gercekci slippage simulasyonu (hacme bagli)
K135: Hacme bagli slippage, liquidity check
"""
import numpy as np
import pandas as pd


class SlippageModel:
    """Gercekci slippage modeli.

    Slippage = base_rate + participation_penalty
    participation_penalty = (order_value / avg_daily_value) * spread_factor
    """

    def __init__(self, base_rate: float = 0.001, max_rate: float = 0.01, spread_factor: float = 5.0):
        self.base_rate = base_rate        # %0.1 baz slippage
        self.max_rate = max_rate          # %1.0 maks slippage
        self.spread_factor = spread_factor

    def calculate(self, order_value: float, avg_daily_volume: float, price: float) -> float:
        """Islem degeri ve gunluk ortalama hacme gore slippage orani dondurur."""
        if avg_daily_volume <= 0 or price <= 0:
            return self.max_rate

        avg_daily_value = avg_daily_volume * price
        participation = order_value / avg_daily_value
        penalty = participation * self.spread_factor
        slippage = self.base_rate + penalty
        return min(slippage, self.max_rate)

    def apply(self, price: float, side: str, order_value: float, avg_daily_volume: float) -> float:
        """Fiyata slippage uygular. Alis = yukari, Satis = asagi."""
        rate = self.calculate(order_value, avg_daily_volume, price)
        if side.upper() == "BUY":
            return price * (1 + rate)
        elif side.upper() == "SELL":
            return price * (1 - rate)
        return price

    def check_liquidity(self, order_value: float, avg_daily_volume: float, price: float) -> bool:
        """Liquidity check: order_value < depth * 0.1 (K135)"""
        depth = avg_daily_volume * price
        return order_value < depth * 0.1


def apply_slippage_to_trades(trades: pd.DataFrame, model: SlippageModel = None, avg_volume_col: str = "volume") -> pd.DataFrame:
    """Trades DataFrame'ine slippage uygular."""
    if model is None:
        model = SlippageModel()

    trades["slippage_rate"] = trades.apply(
        lambda row: model.calculate(
            order_value=row["entry_price"] * row["size"],
            avg_daily_volume=row.get(avg_volume_col, row["size"] * 100),
            price=row["entry_price"],
        ),
        axis=1,
    )
    trades["entry_slippage"] = trades.apply(
        lambda row: model.apply(row["entry_price"], "BUY", row["entry_price"] * row["size"], row.get(avg_volume_col, row["size"] * 100)),
        axis=1,
    )
    trades["exit_slippage"] = trades.apply(
        lambda row: model.apply(row["exit_price"], "SELL", row["exit_price"] * row["size"], row.get(avg_volume_col, row["size"] * 100)) if pd.notna(row.get("exit_price")) else np.nan,
        axis=1,
    )
    return trades
