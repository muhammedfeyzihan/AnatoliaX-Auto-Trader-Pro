"""
fpga/book_update_hw.py — FPGA order book updater
"""


class FPGABookUpdater:
    """
    FPGA L1/L2 book updater.

    Donanim modulu:
    - order_book.v: Seviye-1/2 guncelleme
    - top_level.v: Entegre sinyal uretimi

    K183: FPGA book updater <1us latency hedefi.
    """

    def __init__(self):
        self._top_of_book = {"bid": 0.0, "ask": 0.0}

    def update(self, side: str, price: float, qty: float) -> None:
        self._top_of_book[side] = price

    def get_top(self) -> dict:
        return self._top_of_book
