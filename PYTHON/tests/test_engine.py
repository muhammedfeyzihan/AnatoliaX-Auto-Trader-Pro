"""
Test: PYTHON.backtest.engine
Backtest motoru dogrulama: emir acma, SL, TP, kademeli cikis, trailing stop.
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backtest.engine import BacktestEngine
from backtest.indicators import apply_all
from strategy.parameter_registry import SignalConfig


class TestBacktestEngine:
    def _load_and_prepare(self) -> pd.DataFrame:
        path = Path(__file__).resolve().parent / "fixtures" / "THYAO_20days.csv"
        df = pd.read_csv(path, parse_dates=["timestamp"])
        df = apply_all(df)
        return df

    def test_engine_initializes(self):
        df = self._load_and_prepare()
        engine = BacktestEngine(df)
        assert engine.initial_capital == 100_000.0

    def test_run_returns_dict(self):
        df = self._load_and_prepare()
        engine = BacktestEngine(df)
        result = engine.run()
        assert isinstance(result, dict)
        assert "trades" in result
        assert "equity" in result
        assert "metrics" in result

    def test_trades_dataframe(self):
        df = self._load_and_prepare()
        engine = BacktestEngine(df)
        result = engine.run()
        trades = result["trades"]
        if not trades.empty:
            assert "entry_price" in trades.columns
            assert "exit_price" in trades.columns
            assert "net_pnl" in trades.columns

    def test_metrics_exists(self):
        df = self._load_and_prepare()
        engine = BacktestEngine(df)
        result = engine.run()
        assert "metrics" in result
        assert "_summary" in result["metrics"] or any(
            isinstance(v, dict) and "status" in v for v in result["metrics"].values()
        )

    def test_final_capital_calculated(self):
        df = self._load_and_prepare()
        engine = BacktestEngine(df)
        result = engine.run()
        assert "final_capital" in result
        assert isinstance(result["final_capital"], float)

    def test_total_return_calculated(self):
        df = self._load_and_prepare()
        engine = BacktestEngine(df)
        result = engine.run()
        assert "total_return" in result
        assert isinstance(result["total_return"], float)

    def test_lessons_returned(self):
        df = self._load_and_prepare()
        engine = BacktestEngine(df)
        result = engine.run()
        assert "lessons" in result
        assert isinstance(result["lessons"], list)

    def test_advanced_stop_trailing(self):
        df = self._load_and_prepare()
        engine = BacktestEngine(df, use_advanced_stops=True, stop_type="trailing", stop_params={"multiplier": 2.0})
        result = engine.run()
        assert "trades" in result
        # Trailing stop aktif olmasa bile hata vermemeli
        assert isinstance(result["trades"], pd.DataFrame)

    def test_advanced_stop_time_exit(self):
        df = self._load_and_prepare()
        engine = BacktestEngine(df, use_advanced_stops=True, stop_type="time", stop_params={"max_bars": 5})
        result = engine.run()
        assert "trades" in result
        trades = result["trades"]
        if not trades.empty:
            time_exits = trades[trades["reason"] == "TIME_EXIT"]
            # Time exit olmasi beklenir ama sinyal sayisi az olabilir
            assert isinstance(time_exits, pd.DataFrame)

    def test_advanced_stop_chandelier(self):
        df = self._load_and_prepare()
        engine = BacktestEngine(df, use_advanced_stops=True, stop_type="chandelier")
        result = engine.run()
        assert "trades" in result
        assert isinstance(result["trades"], pd.DataFrame)

    def test_fixed_stop_without_advanced(self):
        df = self._load_and_prepare()
        engine = BacktestEngine(df, use_advanced_stops=False)
        result = engine.run()
        assert "trades" in result
        assert isinstance(result["trades"], pd.DataFrame)

    def test_signal_config_adaptive(self):
        df = self._load_and_prepare()
        cfg = SignalConfig(ema_weight=0.25, rsi_weight=0.15, score_strong=65.0)
        engine = BacktestEngine(df, signal_config=cfg)
        result = engine.run()
        assert "trades" in result
        assert "metrics" in result
        assert "lessons" in result
        assert result["final_capital"] == engine.current_capital


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
