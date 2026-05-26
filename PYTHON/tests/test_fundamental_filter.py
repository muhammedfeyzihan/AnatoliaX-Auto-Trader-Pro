"""
test_fundamental_filter.py — Fundamental Filter Tests
"""

import pytest
from analytics.fundamental_filter import FundamentalFilter, FundamentalData


class TestFundamentalFilter:
    def test_set_sector_benchmark(self):
        f = FundamentalFilter()
        f.set_sector_benchmark("BANKA", pe=8.0, pb=1.0, ev_ebitda=6.0)
        assert f._sector_benchmarks["BANKA"]["pe"] == 8.0

    def test_score_all_pass(self):
        f = FundamentalFilter()
        f.set_sector_benchmark("BANKA", pe=8.0, pb=1.0, ev_ebitda=6.0)
        data = FundamentalData(
            symbol="GARAN",
            sector="BANKA",
            pe=7.0,
            pb=0.9,
            ev_ebitda=5.0,
            net_profit_growth_3y=0.10,
        )
        result = f.score(data)
        assert result["score"] == 100
        assert result["pass"] is True

    def test_score_some_fail(self):
        f = FundamentalFilter()
        f.set_sector_benchmark("BANKA", pe=8.0, pb=1.0, ev_ebitda=6.0)
        data = FundamentalData(
            symbol="GARAN",
            sector="BANKA",
            pe=20.0,
            pb=0.9,
            ev_ebitda=5.0,
            net_profit_growth_3y=0.10,
        )
        result = f.score(data)
        assert result["score"] < 100
        assert result["pass"] is True  # Still >= 40

    def test_score_all_fail(self):
        f = FundamentalFilter()
        f.set_sector_benchmark("BANKA", pe=8.0, pb=1.0, ev_ebitda=6.0)
        data = FundamentalData(
            symbol="GARAN",
            sector="BANKA",
            pe=20.0,
            pb=2.0,
            ev_ebitda=10.0,
            net_profit_growth_3y=-0.05,
        )
        result = f.score(data)
        assert result["pass"] is False

    def test_score_no_benchmark(self):
        f = FundamentalFilter()
        data = FundamentalData(symbol="GARAN", sector="UNKNOWN", pe=10.0)
        result = f.score(data)
        assert result["score"] == 50

    def test_filter_signals_pass(self):
        f = FundamentalFilter()
        f.set_sector_benchmark("BANKA", pe=8.0, pb=1.0, ev_ebitda=6.0)
        signals = [
            {"symbol": "GARAN", "fundamental": FundamentalData(symbol="GARAN", sector="BANKA", pe=7.0, pb=0.9, ev_ebitda=5.0, net_profit_growth_3y=0.10)},
        ]
        filtered = f.filter_signals(signals, min_score=40)
        assert len(filtered) == 1

    def test_filter_signals_fail(self):
        f = FundamentalFilter()
        f.set_sector_benchmark("BANKA", pe=8.0, pb=1.0, ev_ebitda=6.0)
        signals = [
            {"symbol": "GARAN", "fundamental": FundamentalData(symbol="GARAN", sector="BANKA", pe=20.0, pb=2.0, ev_ebitda=10.0, net_profit_growth_3y=-0.05)},
        ]
        filtered = f.filter_signals(signals, min_score=40)
        assert len(filtered) == 0

    def test_filter_signals_no_fundamental(self):
        f = FundamentalFilter()
        signals = [{"symbol": "GARAN"}]
        filtered = f.filter_signals(signals)
        assert len(filtered) == 1

    def test_check_kap_events_no_fetcher(self):
        f = FundamentalFilter()
        result = f.check_kap_events("THYAO")
        assert result["status"] == "UNKNOWN"
