"""
Test: PYTHON.analytics.lesson_generator
Backtest sonuclarindan ders cikarma.
"""
import pytest
import sys
import shutil
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import numpy as np

from analytics.lesson_generator import LessonGenerator


class TestLessonGenerator:
    def test_analyze_backtest_returns_lessons(self):
        trades = pd.DataFrame({
            "entry_idx": [0, 10, 20],
            "exit_idx": [5, 18, 40],
            "entry_price": [100.0, 102.0, 101.0],
            "exit_price": [101.0, 100.0, 105.0],
            "net_pnl": [50.0, -80.0, 120.0],
            "gross_pnl": [55.0, -75.0, 125.0],
            "commission": [5.0, 5.0, 5.0],
            "reason": ["TP1", "SL", "TP2"],
        })
        metrics = {"sharpe_ratio": 0.8, "max_drawdown": -12.5}
        lg = LessonGenerator(output_dir=tempfile.mkdtemp())
        result = lg.analyze_backtest(trades, metrics, symbol="THYAO", strategy="TEST")
        assert "lessons" in result
        assert "action_items" in result
        assert result["symbol"] == "THYAO"
        assert len(result["lessons"]) >= 2
        shutil.rmtree(lg.output_dir, ignore_errors=True)

    def test_empty_trades_returns_no_signal_lesson(self):
        trades = pd.DataFrame(columns=["entry_idx", "exit_idx", "entry_price", "exit_price", "net_pnl", "gross_pnl", "commission", "reason"])
        metrics = {}
        lg = LessonGenerator(output_dir=tempfile.mkdtemp())
        result = lg.analyze_backtest(trades, metrics, symbol="THYAO")
        assert any("No trades" in str(l.get("pattern", "")) for l in result["lessons"])
        shutil.rmtree(lg.output_dir, ignore_errors=True)

    def test_early_sl_detected(self):
        trades = pd.DataFrame({
            "entry_idx": [0, 10],
            "exit_idx": [2, 12],
            "entry_price": [100.0, 102.0],
            "exit_price": [98.0, 100.0],
            "net_pnl": [-100.0, -120.0],
            "gross_pnl": [-95.0, -115.0],
            "commission": [5.0, 5.0],
            "reason": ["SL", "SL"],
        })
        metrics = {"sharpe_ratio": 0.5, "max_drawdown": -5.0}
        lg = LessonGenerator(output_dir=tempfile.mkdtemp())
        result = lg.analyze_backtest(trades, metrics, symbol="THYAO")
        patterns = [l["pattern"] for l in result["lessons"]]
        assert "Erken SL" in patterns
        shutil.rmtree(lg.output_dir, ignore_errors=True)

    def test_profit_factor_suggestion(self):
        trades = pd.DataFrame({
            "entry_idx": [0, 10, 20],
            "exit_idx": [5, 18, 40],
            "entry_price": [100.0, 102.0, 101.0],
            "exit_price": [101.0, 100.0, 105.0],
            "net_pnl": [10.0, -80.0, 15.0],
            "gross_pnl": [15.0, -75.0, 20.0],
            "commission": [5.0, 5.0, 5.0],
            "reason": ["TP1", "SL", "TP2"],
        })
        metrics = {"sharpe_ratio": 0.5, "max_drawdown": -3.0}
        lg = LessonGenerator(output_dir=tempfile.mkdtemp())
        result = lg.analyze_backtest(trades, metrics, symbol="THYAO")
        pf_lessons = [l for l in result["lessons"] if l.get("pattern") == "Win/Loss kalitesi"]
        assert len(pf_lessons) == 1
        assert pf_lessons[0]["profit_factor"] < 1.5
        shutil.rmtree(lg.output_dir, ignore_errors=True)

    def test_get_all_action_items(self):
        td = Path(tempfile.mkdtemp())
        trades = pd.DataFrame({
            "entry_idx": [0],
            "exit_idx": [2],
            "entry_price": [100.0],
            "exit_price": [98.0],
            "net_pnl": [-100.0],
            "gross_pnl": [-95.0],
            "commission": [5.0],
            "reason": ["SL"],
        })
        lg = LessonGenerator(output_dir=td)
        lg.analyze_backtest(trades, {"max_drawdown": -15.0}, symbol="THYAO")
        items = lg.get_all_action_items()
        assert len(items) >= 1
        shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
