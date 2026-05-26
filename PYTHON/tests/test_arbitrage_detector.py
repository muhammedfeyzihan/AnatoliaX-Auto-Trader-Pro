"""
Test: PYTHON.analytics.arbitrage_detector
Cross-venue sapma tespiti, cross-asset korelasyon bozulmasi.
"""
import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from analytics.arbitrage_detector import ArbitrageDetector


class TestArbitrageDetector:
    def test_init(self):
        det = ArbitrageDetector(deviation_threshold_pct=0.8)
        assert det.deviation_threshold == 0.008

    def test_no_opportunity_single_venue(self):
        det = ArbitrageDetector(deviation_threshold_pct=0.5)
        with patch.object(det, "_fetch_multi_venue", return_value=[
            {"venue": "yahoo", "price": 100.0, "timestamp": "2026-05-20", "volume": 1000},
        ]):
            result = det.check_symbol("THYAO")
        assert result is None

    def test_no_opportunity_low_deviation(self):
        det = ArbitrageDetector(deviation_threshold_pct=1.0)
        with patch.object(det, "_fetch_multi_venue", return_value=[
            {"venue": "yahoo", "price": 100.0, "timestamp": "2026-05-20", "volume": 1000},
            {"venue": "bigpara", "price": 100.4, "timestamp": "2026-05-20", "volume": 500},
        ]):
            result = det.check_symbol("THYAO")
        assert result is None

    def test_opportunity_found(self):
        det = ArbitrageDetector(deviation_threshold_pct=0.5)
        with patch.object(det, "_fetch_multi_venue", return_value=[
            {"venue": "yahoo", "price": 100.0, "timestamp": "2026-05-20", "volume": 1000},
            {"venue": "tradingview", "price": 101.0, "timestamp": "2026-05-20", "volume": 800},
        ]):
            result = det.check_symbol("THYAO")
        assert result is not None
        assert result["symbol"] == "THYAO"
        assert result["deviation_pct"] == pytest.approx(0.99, abs=0.01)
        assert result["highest_venue"] == "tradingview"
        assert result["lowest_venue"] == "yahoo"

    def test_scan_universe_sorted(self):
        det = ArbitrageDetector(deviation_threshold_pct=0.5)
        with patch.object(det, "check_symbol", side_effect=[
            {"symbol": "A", "deviation_pct": 1.2},
            None,
            {"symbol": "B", "deviation_pct": 2.5},
        ]):
            results = det.scan_universe(["A", "C", "B"])
        assert len(results) == 2
        assert results[0]["symbol"] == "B"
        assert results[1]["symbol"] == "A"

    def test_format_alert(self):
        opp = {
            "symbol": "THYAO",
            "deviation_pct": 1.5,
            "highest_price": 101.5,
            "lowest_price": 100.0,
            "highest_venue": "yahoo",
            "lowest_venue": "bigpara",
            "cross_asset": None,
        }
        det = ArbitrageDetector()
        msg = det.format_alert(opp)
        assert "Arbitraj Uyari" in msg
        assert "THYAO" in msg
        assert "K145" in msg

    def test_format_alert_with_cross_asset(self):
        opp = {
            "symbol": "THYAO",
            "deviation_pct": 1.5,
            "highest_price": 101.5,
            "lowest_price": 100.0,
            "highest_venue": "yahoo",
            "lowest_venue": "bigpara",
            "cross_asset": {"type": "correlation_breakdown", "description": "test", "score": 0.8},
        }
        det = ArbitrageDetector()
        msg = det.format_alert(opp)
        assert "Cross-Asset" in msg

    def test_check_cross_asset_correlation_low(self):
        det = ArbitrageDetector()
        stock_df = pd.DataFrame({"close": [100.0, 101.0, 102.0, 103.0, 104.0]})
        usdtry_df = pd.DataFrame({"close": [30.0, 30.5, 31.0, 31.5, 32.0]})
        with patch.object(det.feed, "fetch", side_effect=[stock_df, usdtry_df]):
            cross = det._check_cross_asset("THYAO.IS")
        assert cross is None  # yuksek korelasyon

    def test_check_cross_asset_correlation_breakdown(self):
        det = ArbitrageDetector()
        stock_df = pd.DataFrame({"close": [100.0, 101.0, 102.0, 103.0, 104.0]})
        usdtry_df = pd.DataFrame({"close": [32.0, 31.0, 30.0, 29.0, 28.0]})
        with patch.object(det.feed, "fetch", side_effect=[stock_df, usdtry_df]):
            cross = det._check_cross_asset("THYAO")
        if cross:
            assert cross["type"] == "correlation_breakdown"
            assert "score" in cross

    def test_fetch_multi_venue_empty(self):
        det = ArbitrageDetector()
        with patch.object(det.feed, "fetch", return_value=pd.DataFrame()):
            prices = det._fetch_multi_venue("THYAO")
        assert prices == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
