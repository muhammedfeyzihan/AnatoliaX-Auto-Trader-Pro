"""
tests/test_order_book.py — OrderBook birim testleri
"""
import pytest
from hft_pro.feed.book_reconstructor import OrderBook
from decimal import Decimal


class TestOrderBook:
    def test_mid_price(self):
        book = OrderBook("THYAO")
        book.add_order("o1", Decimal("100"), Decimal("10"), "BUY")
        book.add_order("o2", Decimal("101"), Decimal("10"), "SELL")
        assert book.mid_price == Decimal("100.50")

    def test_spread(self):
        book = OrderBook("THYAO")
        book.add_order("o1", Decimal("100"), Decimal("10"), "BUY")
        book.add_order("o2", Decimal("102"), Decimal("10"), "SELL")
        assert book.spread == Decimal("2")

    def test_detect_spoofing(self):
        book = OrderBook("THYAO")
        book.add_order("s1", Decimal("100"), Decimal("10000"), "BUY")
        book.cancel_order("s1")
        assert book.detect_spoofing() is True
