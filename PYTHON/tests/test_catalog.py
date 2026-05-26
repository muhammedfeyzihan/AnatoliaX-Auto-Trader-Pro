"""
Test: PYTHON.data.catalog
DataCatalog: write, read, metadata, coverage.
"""
import pytest
import pandas as pd
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.catalog import DataCatalog


class TestDataCatalog:
    @pytest.fixture
    def catalog(self):
        tmpdir = tempfile.mkdtemp()
        cat = DataCatalog(base_dir=tmpdir)
        yield cat
        shutil.rmtree(tmpdir, ignore_errors=True)

    def _make_bar_df(self, n=10, start_date="2026-05-01"):
        timestamps = pd.date_range(start_date, periods=n, freq="D")
        return pd.DataFrame({
            "timestamp": timestamps,
            "open": [100.0 + i for i in range(n)],
            "high": [102.0 + i for i in range(n)],
            "low": [99.0 + i for i in range(n)],
            "close": [101.0 + i for i in range(n)],
            "volume": [1000000 + i * 10000 for i in range(n)],
        })

    def test_write_and_read_bars(self, catalog):
        df = self._make_bar_df(5)
        catalog.write_bars("THYAO", df, interval="1d")
        result = catalog.read_bars("THYAO", interval="1d")
        assert len(result) == 5
        assert list(result.columns) == ["timestamp", "open", "high", "low", "close", "volume"]

    def test_read_bars_with_date_range(self, catalog):
        df = self._make_bar_df(10, start_date="2026-05-01")
        catalog.write_bars("THYAO", df, interval="1d")
        start = datetime(2026, 5, 3, tzinfo=timezone.utc)
        end = datetime(2026, 5, 7, tzinfo=timezone.utc)
        result = catalog.read_bars("THYAO", interval="1d", start=start, end=end)
        # Date filter on timestamps should return 5 rows (May 3-7)
        assert len(result) == 5

    def test_list_symbols(self, catalog):
        df = self._make_bar_df(3)
        catalog.write_bars("THYAO", df, interval="1d")
        catalog.write_bars("GARAN", df, interval="1d")
        symbols = catalog.list_symbols(data_type="bar")
        assert set(symbols) == {"THYAO", "GARAN"}

    def test_list_intervals(self, catalog):
        df = self._make_bar_df(3)
        catalog.write_bars("THYAO", df, interval="1d")
        catalog.write_bars("THYAO", df, interval="15m")
        intervals = catalog.list_intervals("THYAO")
        assert set(intervals) == {"1d", "15m"}

    def test_get_coverage(self, catalog):
        df = self._make_bar_df(5)
        catalog.write_bars("THYAO", df, interval="1d")
        cov = catalog.get_coverage("THYAO", interval="1d")
        assert cov["symbol"] == "THYAO"
        assert cov["interval"] == "1d"
        assert cov["rows"] == 5
        assert cov["date_from"] is not None
        assert cov["date_to"] is not None

    def test_stats(self, catalog):
        df = self._make_bar_df(3)
        catalog.write_bars("THYAO", df, interval="1d")
        stats = catalog.stats()
        assert stats["total_files"] == 3  # 3 daily files
        assert stats["unique_symbols"] == 1

    def test_delete_symbol(self, catalog):
        df = self._make_bar_df(3)
        catalog.write_bars("THYAO", df, interval="1d")
        catalog.delete_symbol("THYAO", data_type="bar")
        assert catalog.read_bars("THYAO", interval="1d").empty
        assert catalog.list_symbols(data_type="bar") == []

    def test_write_bars_empty_raises(self, catalog):
        with pytest.raises(ValueError):
            catalog.write_bars("THYAO", pd.DataFrame(), interval="1d")

    def test_write_ticks(self, catalog):
        df = pd.DataFrame({
            "timestamp": pd.date_range("2026-05-01", periods=5, freq="min"),
            "price": [100.0, 100.1, 100.2, 100.3, 100.4],
            "size": [10, 20, 15, 30, 25],
        })
        path = catalog.write_ticks("THYAO", df, month="2026-05")
        result = catalog.read_ticks("THYAO")
        assert len(result) == 5
        assert "price" in result.columns

    def test_read_nonexistent_symbol_returns_empty(self, catalog):
        result = catalog.read_bars("NONEXIST", interval="1d")
        assert result.empty
