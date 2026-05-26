"""
Test: PYTHON.analytics.error_analyzer
ErrorAnalyzer hata kayit ve analiz.
"""
import pytest
import sys
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from analytics.error_analyzer import ErrorAnalyzer


class TestErrorAnalyzer:
    def setup_method(self):
        self.td = tempfile.mkdtemp()
        self.analyzer = ErrorAnalyzer(log_dir=self.td)

    def teardown_method(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def test_log_error(self):
        rec = self.analyzer.log_error(
            symbol="THYAO",
            agent="B",
            expected="AL",
            actual="SAT",
            market_regime="BULL",
            pnl_impact=-500.0,
            root_cause_category="teknik",
        )
        assert rec["symbol"] == "THYAO"
        assert rec["agent"] == "B"
        assert rec["pnl_impact"] == -500.0
        assert len(self.analyzer.errors) == 1

    def test_load_existing(self):
        self.analyzer.log_error("THYAO", "B", "AL", "SAT", "BULL")
        # Yeni instance olustur, eski kayitlari yuklesin
        analyzer2 = ErrorAnalyzer(log_dir=self.td)
        assert len(analyzer2.errors) == 1
        assert analyzer2.errors[0]["symbol"] == "THYAO"

    def test_analyze_patterns_empty(self):
        result = self.analyzer.analyze_patterns(agent="B")
        assert "message" in result

    def test_analyze_patterns_with_data(self):
        for i in range(5):
            self.analyzer.log_error("THYAO", "B", "AL", "SAT", "BULL", pnl_impact=-100.0 * (i + 1), root_cause_category="teknik")
        result = self.analyzer.analyze_patterns()
        assert result["total_errors"] == 5
        assert result["total_impact_tl"] < 0
        assert "B" in result["agent_distribution"]
        assert "teknik" in result["root_cause_distribution"]

    def test_suggest_rule_update(self):
        for i in range(3):
            self.analyzer.log_error("THYAO", "B", "AL", "SAT", "BULL", root_cause_category="teknik")
        suggestions = self.analyzer.suggest_rule_update()
        assert len(suggestions) > 0
        assert "rule_id" in suggestions[0]
        assert "K" in suggestions[0]["rule_id"]

    def test_log_error_with_missed_signals(self):
        rec = self.analyzer.log_error(
            symbol="GARAN",
            agent="C",
            expected="BOGA",
            actual="AYI",
            market_regime="NEUTRAL",
            missed_signals=["gap_up", "volume_spike"],
        )
        assert rec["missed_signals"] == ["gap_up", "volume_spike"]

    def test_jsonl_format(self):
        self.analyzer.log_error("THYAO", "B", "AL", "SAT", "BULL")
        log_path = Path(self.td) / "anatoliax_errors.jsonl"
        assert log_path.exists()
        with open(log_path, "r", encoding="utf-8") as f:
            line = json.loads(f.readline().strip())
        assert line["symbol"] == "THYAO"

    def test_filter_by_agent(self):
        self.analyzer.log_error("THYAO", "B", "AL", "SAT", "BULL")
        self.analyzer.log_error("GARAN", "C", "AL", "SAT", "BULL")
        result = self.analyzer.analyze_patterns(agent="B")
        assert result["total_errors"] == 1
        assert "B" in result["agent_distribution"]
        assert "C" not in result["agent_distribution"]

    def test_recurring_errors(self):
        for i in range(5):
            self.analyzer.log_error("THYAO", "B", "AL", "SAT", "BULL", root_cause_category="teknik")
        result = self.analyzer.analyze_patterns()
        assert result["needs_rule_update"] is True
        assert len(result["recurring_errors"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
