"""
Test: PYTHON.observability.performance_logger
PerformanceLogger trade/agent prediction logging.
"""
import pytest
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from observability.performance_logger import PerformanceLogger


class TestPerformanceLogger:
    def setup_method(self):
        self.td = tempfile.mkdtemp()
        self.db = Path(self.td) / "perf.db"
        self.logger = PerformanceLogger(self.db)

    def teardown_method(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def test_log_trade_win(self):
        self.logger.log_trade(trade_id=1, symbol="THYAO", entry_price=100.0, exit_price=110.0, actual_pnl=1000.0, agent="Sinyal")
        summary = self.logger.get_daily_summary()
        assert summary["win"] == 1
        assert summary["total_pnl"] == 1000.0

    def test_log_trade_loss(self):
        self.logger.log_trade(trade_id=2, symbol="GARAN", entry_price=100.0, exit_price=90.0, actual_pnl=-500.0, agent="Risk")
        summary = self.logger.get_daily_summary()
        assert summary["loss"] == 1
        assert summary["total_pnl"] == -500.0

    def test_log_trade_breakeven(self):
        self.logger.log_trade(trade_id=3, symbol="ASELS", entry_price=100.0, exit_price=100.0, actual_pnl=0.0, agent="Strateji")
        summary = self.logger.get_daily_summary()
        assert summary["breakeven"] == 1

    def test_log_trade_pending(self):
        self.logger.log_trade(trade_id=4, symbol="BIMAS", entry_price=100.0, actual_pnl=0.0, agent="Sinyal")
        summary = self.logger.get_daily_summary()
        assert summary["pending"] == 1

    def test_log_prediction_and_update(self):
        self.logger.log_prediction(symbol="THYAO", agent="Sinyal", prediction="UP", confidence=75.0, market_regime="BULL")
        self.logger.update_prediction_result(symbol="THYAO", agent="Sinyal", actual_result="UP")
        acc = self.logger.get_agent_accuracy("Sinyal")
        assert acc["total"] == 1
        assert acc["correct"] == 1
        assert acc["accuracy"] == 100.0

    def test_update_prediction_wrong(self):
        self.logger.log_prediction(symbol="THYAO", agent="Sinyal", prediction="UP", confidence=75.0)
        self.logger.update_prediction_result(symbol="THYAO", agent="Sinyal", actual_result="DOWN")
        acc = self.logger.get_agent_accuracy("Sinyal")
        assert acc["total"] == 1
        assert acc["correct"] == 0
        assert acc["accuracy"] == 0.0

    def test_get_agent_accuracy_empty(self):
        acc = self.logger.get_agent_accuracy("NonExistent", days=30)
        assert acc["total"] == 0
        assert acc["accuracy"] == 0.0

    def test_get_learning_insights(self):
        self.logger.log_prediction(symbol="THYAO", agent="Sinyal", prediction="UP", confidence=75.0, market_regime="BULL")
        self.logger.update_prediction_result(symbol="THYAO", agent="Sinyal", actual_result="DOWN")
        insights = self.logger.get_learning_insights(days=30)
        assert len(insights) >= 0
        assert "pattern" in insights[0]
        assert "suggestion" in insights[0]

    def test_get_daily_summary_empty(self):
        summary = self.logger.get_daily_summary("2020-01-01")
        assert summary["win"] == 0
        assert summary["loss"] == 0
        assert summary["total_pnl"] == 0.0

    def test_init_db_idempotent(self):
        # Ikinci cagri hata vermemeli
        logger2 = PerformanceLogger(self.db)
        assert logger2 is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
