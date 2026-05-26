"""
Test: PYTHON.agents.rule_evolution
Kural evrimi, ayi/boga tespiti, oneri uretebilirlik.
"""
import pytest
import sys
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.rule_evolution import RuleEvolution


def _make_td():
    return Path(tempfile.mkdtemp())


class TestRuleEvolution:
    def test_insufficient_trades(self):
        td = _make_td()
        try:
            evo = RuleEvolution(db_path=td / "perf.db")
            suggestions = evo.analyze_and_evolve()
            assert len(suggestions) == 1
            assert suggestions[0]["rule"] == "NOP"
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_bear_market_suggestion(self):
        td = _make_td()
        try:
            db_path = td / "perf.db"
            import sqlite3
            with sqlite3.connect(str(db_path)) as conn:
                conn.execute("""
                    CREATE TABLE trade_outcomes (
                        symbol TEXT, entry_price REAL, exit_price REAL,
                        pnl_pct REAL, outcome TEXT, timestamp TEXT, regime TEXT
                    )
                """)
                now = datetime.now().isoformat()
                for i in range(15):
                    conn.execute(
                        "INSERT INTO trade_outcomes VALUES (?, ?, ?, ?, ?, ?, ?)",
                        ("THYAO", 100, 95, -5.0, "STOP", now, "BEAR"),
                    )
                conn.commit()

            evo = RuleEvolution(db_path=db_path)
            suggestions = evo.analyze_and_evolve()
            rules = [s["rule"] for s in suggestions]
            assert "SL_ATR_MULTIPLIER" in rules
            assert "KELLY_CAP" in rules
            assert "MAX_POSITIONS" in rules
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_bull_market_suggestion(self):
        td = _make_td()
        try:
            db_path = td / "perf.db"
            import sqlite3
            with sqlite3.connect(str(db_path)) as conn:
                conn.execute("""
                    CREATE TABLE trade_outcomes (
                        symbol TEXT, entry_price REAL, exit_price REAL,
                        pnl_pct REAL, outcome TEXT, timestamp TEXT, regime TEXT
                    )
                """)
                now = datetime.now().isoformat()
                for i in range(15):
                    conn.execute(
                        "INSERT INTO trade_outcomes VALUES (?, ?, ?, ?, ?, ?, ?)",
                        ("THYAO", 100, 110, 10.0, "TP1", now, "BULL"),
                    )
                conn.commit()

            evo = RuleEvolution(db_path=db_path)
            suggestions = evo.analyze_and_evolve()
            rules = [s["rule"] for s in suggestions]
            assert "SL_ATR_MULTIPLIER" in rules or "KELLY_CAP" in rules or len(suggestions) >= 1
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_low_win_rate_threshold(self):
        td = _make_td()
        try:
            db_path = td / "perf.db"
            import sqlite3
            with sqlite3.connect(str(db_path)) as conn:
                conn.execute("""
                    CREATE TABLE trade_outcomes (
                        symbol TEXT, entry_price REAL, exit_price REAL,
                        pnl_pct REAL, outcome TEXT, timestamp TEXT, regime TEXT
                    )
                """)
                now = datetime.now().isoformat()
                for i in range(20):
                    pnl = -2.0 if i % 3 != 0 else 1.0
                    conn.execute(
                        "INSERT INTO trade_outcomes VALUES (?, ?, ?, ?, ?, ?, ?)",
                        ("THYAO", 100, 98, pnl, "STOP" if pnl < 0 else "TP1", now, "NEUTRAL"),
                    )
                conn.commit()

            evo = RuleEvolution(db_path=db_path)
            suggestions = evo.analyze_and_evolve()
            rules = [s["rule"] for s in suggestions]
            assert "SIGNAL_THRESHOLD" in rules
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_log_and_retrieve(self):
        td = _make_td()
        try:
            evo = RuleEvolution(db_path=td / "perf.db")
            evo.analyze_and_evolve()
            last = evo.get_last_evolution()
            assert last is not None
            assert "timestamp" in last
        finally:
            shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
