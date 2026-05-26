"""
Test: PYTHON.main (orchestrator)
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import main as main_mod


class TestMain:
    def test_init_db(self):
        with patch("main.database.init_db") as mock_init:
            main_mod.init_db()
            mock_init.assert_called_once()

    def test_run_backtest(self, tmp_path):
        csv = tmp_path / "test.csv"
        csv.write_text("timestamp,open,high,low,close,volume\n2024-01-01,100,110,90,105,10000\n2024-01-02,105,115,100,110,12000\n2024-01-03,110,120,105,115,15000\n2024-01-04,115,125,110,120,14000\n2024-01-05,120,130,115,125,16000\n")
        with patch("main.dashboard.cli_table", return_value="table"):
            result = main_mod.run_backtest(str(csv), symbol="TEST")
            assert result is not None

    def test_run_analytics(self, tmp_path):
        csv = tmp_path / "test.csv"
        csv.write_text("timestamp,open,high,low,close,volume\n2024-01-01,100,110,90,105,10000\n2024-01-02,105,115,100,110,12000\n2024-01-03,110,120,105,115,15000\n2024-01-04,115,125,110,120,14000\n2024-01-05,120,130,115,125,16000\n")
        main_mod.run_analytics(str(csv))

    def test_run_monitor(self):
        with patch("main.portfolio_monitor.PortfolioMonitor.get_portfolio_summary", return_value={"cash": 1000}):
            main_mod.run_monitor()

    def test_main_help(self):
        with patch("sys.argv", ["main.py", "--help"]), pytest.raises(SystemExit):
            main_mod.main()

    def test_hft_backtest_arg(self, tmp_path):
        csv = tmp_path / "ticks.csv"
        csv.write_text("timestamp,price,size,symbol\n2024-01-01 09:30:00,100.0,10,THYAO\n2024-01-01 09:30:01,101.0,20,THYAO\n")
        with patch("sys.argv", ["main.py", "--hft-backtest", str(csv), "--hft-strategy", "m1_momentum"]):
            main_mod.main()

    def test_hft_live_arg(self):
        with patch("sys.argv", ["main.py", "--hft-live", "THYAO,GARAN"]):
            with patch("main.FeedAggregator") as mock_feed:
                mock_feed.return_value.fetch.return_value = None
                main_mod.main()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
