"""
Test: PYTHON.backtest.chart_generator
Bokeh/Matplotlib fallback grafik uretimi.
"""
import pytest
import sys
import shutil
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import numpy as np

from backtest.chart_generator import BacktestChartGenerator


class TestBacktestChartGenerator:
    def _make_data(self):
        rows = 100
        idx = pd.date_range("2026-01-01", periods=rows, freq="D")
        df = pd.DataFrame({
            "open": np.cumsum(np.random.randn(rows)) + 100,
            "high": np.cumsum(np.random.randn(rows)) + 102,
            "low": np.cumsum(np.random.randn(rows)) + 98,
            "close": np.cumsum(np.random.randn(rows)) + 100,
            "volume": np.ones(rows) * 1_000_000,
            "EMA9": np.cumsum(np.random.randn(rows)) + 100,
            "EMA21": np.cumsum(np.random.randn(rows)) + 100,
        }, index=idx)
        trades = pd.DataFrame({
            "entry_idx": [10, 50],
            "exit_idx": [20, 65],
            "entry_price": [100.0, 105.0],
            "exit_price": [102.0, 104.0],
            "reason": ["TP1", "SL"],
            "net_pnl": [200.0, -150.0],
        })
        equity = pd.DataFrame({"equity": np.cumsum(np.random.randn(rows) * 100) + 100_000}, index=idx)
        return df, trades, equity

    def test_create_charts_returns_html(self):
        df, trades, equity = self._make_data()
        gen = BacktestChartGenerator(df, trades, equity, title="Test")
        html = gen.create_charts()
        assert isinstance(html, str)
        assert "html" in html.lower()

    def test_save_html_creates_file(self):
        td = Path(tempfile.mkdtemp())
        try:
            df, trades, equity = self._make_data()
            gen = BacktestChartGenerator(df, trades, equity)
            out = td / "backtest_test.html"
            path = gen.save_html(out)
            assert path.exists()
            content = path.read_text(encoding="utf-8")
            assert len(content) > 1000
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_drawdown_calculation(self):
        df, trades, equity = self._make_data()
        gen = BacktestChartGenerator(df, trades, equity)
        dd = gen._calculate_drawdown()
        assert isinstance(dd, pd.Series)
        assert dd.min() <= 0

    def test_empty_trades_fallback(self):
        df, _, equity = self._make_data()
        gen = BacktestChartGenerator(df, pd.DataFrame(), equity)
        html = gen.create_charts()
        assert isinstance(html, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
