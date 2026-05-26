"""
test_paper_live_separator.py — Paper/Live Separator Tests
"""

import pytest
from execution.paper_live_separator import (
    PaperLiveSeparator,
    ExecutionQualityScore,
    ExecutionOutcome,
)


class TestExecutionQualityScore:
    def test_calculate_perfect(self):
        eqs = ExecutionQualityScore()
        score = eqs.calculate(fill_rate=1.0, avg_slippage=0.0, latency_ms=0.0, market_impact=0.0)
        assert score == 100.0

    def test_calculate_high_latency(self):
        eqs = ExecutionQualityScore(max_latency_ms=100.0)
        score = eqs.calculate(fill_rate=1.0, avg_slippage=0.0, latency_ms=500.0, market_impact=0.0)
        assert score < 100.0

    def test_calculate_low_fill(self):
        eqs = ExecutionQualityScore()
        score = eqs.calculate(fill_rate=0.5, avg_slippage=0.0, latency_ms=0.0, market_impact=0.0)
        assert score == 85.0  # 0.5 * 0.30 = 15 loss


class TestPaperLiveSeparator:
    def test_run_paper(self):
        sep = PaperLiveSeparator()
        signal = {"id": "s1", "symbol": "THYAO", "side": "BUY", "size": 10, "price": 100.0}
        outcome = sep.run_paper(signal)
        assert outcome.latency_ms == 0.0
        assert outcome.fill_rate == 1.0
        assert outcome.slippage == 0.0

    def test_run_live(self):
        sep = PaperLiveSeparator()
        signal = {"id": "s1", "symbol": "THYAO", "side": "BUY", "size": 10, "price": 100.0}
        outcome = sep.run_live(signal, filled_price=100.2, latency_ms=150.0)
        assert outcome.latency_ms == 150.0
        assert outcome.slippage == pytest.approx(0.002, rel=1e-6)

    def test_latency_stats(self):
        sep = PaperLiveSeparator()
        for i in range(10):
            signal = {"id": f"s{i}", "symbol": "THYAO", "side": "BUY", "size": 10, "price": 100.0}
            sep.run_live(signal, filled_price=100.0, latency_ms=float(i * 10))
        stats = sep.latency_stats()
        assert stats["count"] == 10
        assert stats["p50"] >= 0
        assert stats["p95"] >= stats["p50"]

    def test_latency_stats_empty(self):
        sep = PaperLiveSeparator()
        stats = sep.latency_stats()
        assert stats["count"] == 0

    def test_reconcile_aligned(self):
        sep = PaperLiveSeparator()
        signal = {"id": "s1", "symbol": "THYAO", "side": "BUY", "size": 10, "price": 100.0}
        sep.run_paper(signal)
        sep.run_live(signal, filled_price=100.0, latency_ms=50.0)
        result = sep.reconcile()
        assert result["alert"] is False
        assert "aligned" in result["reason"]

    def test_reconcile_alert(self):
        sep = PaperLiveSeparator()
        signal = {"id": "s1", "symbol": "THYAO", "side": "BUY", "size": 10, "price": 100.0}
        sep.run_paper(signal)
        sep.run_live(signal, filled_price=102.0, latency_ms=50.0)  # 2% slippage
        result = sep.reconcile()
        assert result["alert"] is True

    def test_reconcile_no_data(self):
        sep = PaperLiveSeparator()
        result = sep.reconcile()
        assert result["difference_pct"] is None
        assert result["pairs"] == []

    def test_reconcile_pairs_by_signal_id(self):
        sep = PaperLiveSeparator()
        s1 = {"id": "s1", "symbol": "THYAO", "side": "BUY", "size": 10, "price": 100.0}
        s2 = {"id": "s2", "symbol": "GARAN", "side": "BUY", "size": 5, "price": 50.0}
        sep.run_paper(s1)
        sep.run_paper(s2)
        sep.run_live(s1, filled_price=100.0, latency_ms=50.0)
        sep.run_live(s2, filled_price=51.0, latency_ms=60.0)  # 2% slippage for s2
        result = sep.reconcile()
        assert len(result["pairs"]) == 2
        # s1 should be aligned
        s1_pair = next(p for p in result["pairs"] if p["signal_id"] == "s1")
        assert s1_pair["alert"] is False
        # s2 should alert (2% slippage > 1% threshold)
        s2_pair = next(p for p in result["pairs"] if p["signal_id"] == "s2")
        assert s2_pair["alert"] is True

    def test_reconcile_mismatch(self):
        sep = PaperLiveSeparator()
        s1 = {"id": "s1", "symbol": "THYAO", "side": "BUY", "size": 10, "price": 100.0}
        sep.run_paper(s1)
        # No live for s1, live for s2 only
        s2 = {"id": "s2", "symbol": "GARAN", "side": "BUY", "size": 5, "price": 50.0}
        sep.run_live(s2, filled_price=50.0, latency_ms=50.0)
        result = sep.reconcile()
        assert result["mismatches"] == 2
        assert len(result["pairs"]) == 0

    def test_calculate_eqs(self):
        sep = PaperLiveSeparator()
        signal = {"id": "s1", "symbol": "THYAO", "side": "BUY", "size": 10, "price": 100.0}
        sep.run_live(signal, filled_price=100.0, latency_ms=0.0)
        eqs = sep.calculate_eqs()
        assert eqs > 0

    def test_calculate_eqs_empty(self):
        sep = PaperLiveSeparator()
        assert sep.calculate_eqs() == 0.0

    def test_daily_summary(self):
        sep = PaperLiveSeparator()
        signal = {"id": "s1", "symbol": "THYAO", "side": "BUY", "size": 10, "price": 100.0}
        sep.run_paper(signal)
        sep.run_live(signal, filled_price=100.0, latency_ms=50.0)
        summary = sep.daily_summary()
        assert summary["paper_trades"] == 1
        assert summary["live_trades"] == 1
        assert "eqs" in summary
        assert "latency" in summary
