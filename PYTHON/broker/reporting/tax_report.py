"""
reporting/tax_report.py — Turk vergi duzenlemelerine uygun raporlama
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import List


@dataclass
class TradeLine:
    symbol: str
    buy_date: str
    sell_date: str
    buy_price: Decimal
    sell_price: Decimal
    quantity: Decimal
    gross_pnl: Decimal
    commission: Decimal
    bsmv: Decimal
    net_pnl: Decimal


class TaxReporter:
    """
    Turk vergi duzenlemelerine uygun islem raporu.

    Rapor kapsami:
    - Her islem icin: alis tarihi, satis tarihi, fiyatlar, miktar, brut PnL
    - Komisyon + BSMV ayrintilari
    - Net PnL = Brut - Komisyon - BSMV
    - Stopaj dahil degil (bireysel yatirimci stopaji %0, 2026)

    Cikti:
    - CSV (Mali musavir icin)
    - JSON (otomatik sistem icin)
    """

    def __init__(self, trades: List[TradeLine] = None):
        self._trades = trades or []

    def add_trade(self, trade: TradeLine) -> None:
        self._trades.append(trade)

    def generate_csv(self, path: str) -> None:
        import csv
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Sembol", "Alis", "Satis", "Alis Fiyati", "Satis Fiyati",
                             "Miktar", "Brut PnL", "Komisyon", "BSMV", "Net PnL"])
            for t in self._trades:
                writer.writerow([t.symbol, t.buy_date, t.sell_date, t.buy_price, t.sell_price,
                                 t.quantity, t.gross_pnl, t.commission, t.bsmv, t.net_pnl])

    def total_net_pnl(self) -> Decimal:
        return sum((t.net_pnl for t in self._trades), Decimal("0"))
