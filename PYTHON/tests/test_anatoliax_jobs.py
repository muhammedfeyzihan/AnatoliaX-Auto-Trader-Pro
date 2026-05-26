"""
Test: PYTHON.scheduler.anatoliax_jobs
AnatoliaXJobs zamanlanmis gorev kayit.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scheduler.anatoliax_jobs import AnatoliaXJobs, register_all_jobs
from scheduler.task_scheduler import TaskScheduler


class TestAnatoliaXJobs:
    def test_register_all(self):
        sched = TaskScheduler()
        jobs = AnatoliaXJobs(sched)
        jobs.register_all()
        registered = sched.list_jobs()
        ids = [j["id"] for j in registered]
        assert "signal_scan_15m" in ids
        assert "risk_check_1h" in ids
        assert "morning_report" in ids
        assert "opening_report" in ids
        assert "midday_report" in ids
        assert "evening_report" in ids
        assert "health_check" in ids
        assert "subscription_check_5m" in ids
        assert "rule_evolution_1630" in ids

    def test_register_all_jobs_helper(self):
        sched = TaskScheduler()
        register_all_jobs(sched)
        registered = sched.list_jobs()
        assert len(registered) >= 9

    def test_signal_scan_job(self):
        sched = TaskScheduler()
        jobs = AnatoliaXJobs(sched)
        with patch("paper_trading.signal_engine.SignalEngine") as mock_engine:
            mock_engine.return_value.run_scan.return_value = []
            jobs._register_signal_scan()
            # Scheduler'a eklenmis olmali
            assert any(j["id"] == "signal_scan_15m" for j in sched.list_jobs())

    def test_risk_check_job(self):
        sched = TaskScheduler()
        jobs = AnatoliaXJobs(sched)
        with patch("risk.kill_switch.KillSwitch") as mock_ks:
            mock_ks.return_value.is_trading_allowed.return_value = True
            jobs._register_risk_check()
            assert any(j["id"] == "risk_check_1h" for j in sched.list_jobs())

    def test_morning_report_job(self):
        sched = TaskScheduler()
        jobs = AnatoliaXJobs(sched)
        with patch("telegram.reporter.send_report") as mock_send:
            jobs._register_morning_report()
            assert any(j["id"] == "morning_report" for j in sched.list_jobs())

    def test_evening_report_job(self):
        sched = TaskScheduler()
        jobs = AnatoliaXJobs(sched)
        with patch("telegram.reporter.send_report") as mock_send:
            jobs._register_evening_report()
            assert any(j["id"] == "evening_report" for j in sched.list_jobs())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
