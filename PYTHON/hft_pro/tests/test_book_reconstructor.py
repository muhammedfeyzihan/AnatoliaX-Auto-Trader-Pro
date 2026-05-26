"""
tests/test_book_reconstructor.py — OrderBook birim testleri
"""
import pytest
from hft_pro.feed.book_reconstructor import OrderBook
from decimal import Decimal


class TestBookReconstructor:
    def test_l3_depth(self):
        book = OrderBook("THYAO")
        for i in range(10):
            book.add_order(f"o{i}", Decimal(str(100 + i)), Decimal("10"), "BUY")
        assert book.get_level_size("BUY", Decimal("105")) == Decimal("10")

    def test_spoofing_sequence(self):
        book = OrderBook("THYAO")
        book.add_order("s1", Decimal("100"), Decimal("5000"), "BUY")
        book.cancel_order("s1")
        assert book.detect_spoofing() is True
