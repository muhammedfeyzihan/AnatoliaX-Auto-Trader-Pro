"""
tests/test_feed_handler.py — FeedHandler birim testleri
"""
import pytest
from hft_pro.feed.feed_handler import FeedHandler


class TestFeedHandler:
    def test_tick_parsing(self):
        fh = FeedHandler(port=12345)
        tick = fh._parse_packet(b"THYAO,100.50,1000,1234567890")
        assert tick.symbol == "THYAO"
        assert float(tick.price) == 100.50

    def test_gap_stats_empty(self):
        fh = FeedHandler(port=12345)
        assert fh.gap_stats() == 0.0
