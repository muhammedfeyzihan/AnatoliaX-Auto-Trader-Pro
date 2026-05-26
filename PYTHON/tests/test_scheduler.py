"""
Test: PYTHON.scheduler.task_scheduler
Cron parse, job ekleme, log.
"""
import pytest
import sys
import shutil
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scheduler.task_scheduler import TaskScheduler


def _make_td():
    return Path(tempfile.mkdtemp())


class TestTaskScheduler:
    def test_init(self):
        td = _make_td()
        try:
            sched = TaskScheduler(db_path=td / "tasks.db")
            assert sched.db_path.exists()
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_add_interval_job(self):
        def dummy():
            pass

        td = _make_td()
        try:
            sched = TaskScheduler(db_path=td / "tasks.db")
            jid = sched.add_interval_job(dummy, minutes=15, job_id="scan")
            assert jid == "scan"
            assert "scan" in [j["id"] for j in sched.list_jobs()]
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_add_daily_job(self):
        def dummy():
            pass

        td = _make_td()
        try:
            sched = TaskScheduler(db_path=td / "tasks.db")
            jid = sched.add_daily_job(dummy, hour=8, minute=30, job_id="morning")
            assert jid == "morning"
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_remove_job(self):
        def dummy():
            pass

        td = _make_td()
        try:
            sched = TaskScheduler(db_path=td / "tasks.db")
            jid = sched.add_interval_job(dummy, minutes=15)
            assert sched.remove_job(jid) is True
            assert sched.remove_job(jid) is False
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_task_log(self):
        def dummy():
            pass

        td = _make_td()
        try:
            sched = TaskScheduler(db_path=td / "tasks.db")
            sched.add_interval_job(dummy, minutes=15, job_id="scan")
            logs = sched.get_task_log()
            assert len(logs) >= 1
            assert logs[0]["id"] == "scan"
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_update_last_run(self):
        def dummy():
            pass

        td = _make_td()
        try:
            sched = TaskScheduler(db_path=td / "tasks.db")
            sched.add_interval_job(dummy, minutes=15, job_id="scan")
            sched.update_last_run("scan")
            logs = sched.get_task_log()
            assert any(l["id"] == "scan" and l["last_run"] is not None for l in logs)
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_rule_evolution_job_registration(self):
        td = _make_td()
        try:
            from scheduler.anatoliax_jobs import AnatoliaXJobs
            sched = TaskScheduler(db_path=td / "tasks.db")
            jobs = AnatoliaXJobs(sched)
            jobs._register_rule_evolution()
            ids = [j["id"] for j in sched.list_jobs()]
            assert "rule_evolution_1630" in ids
        finally:
            shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
