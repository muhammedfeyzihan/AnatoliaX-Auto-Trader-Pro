"""
task_scheduler.py — Cron benzeri zamanlayici servisi.
auto-marketplace'tan entegre edilmistir.

Kullanim:
    from scheduler.task_scheduler import TaskScheduler
    sched = TaskScheduler()
    sched.add_interval_job(func, minutes=15, id="signal_scan")
    sched.add_daily_job(func, hour=8, minute=30, id="morning_report")
    sched.start()
"""
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

import sqlite3
import json
from datetime import datetime
from typing import Callable, Optional


try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger

    APSCHEDULER_AVAILABLE = True
except Exception:
    BackgroundScheduler = None
    CronTrigger = None
    IntervalTrigger = None
    APSCHEDULER_AVAILABLE = False


DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "scheduled_tasks.db"


class TaskScheduler:
    """
    Zamanlanmis gorev yoneticisi.
    APScheduler varsa kullanir, yoksa basit polling fallback.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._jobs: dict[str, dict] = {}
        self._scheduler = None
        if APSCHEDULER_AVAILABLE:
            self._scheduler = BackgroundScheduler()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id TEXT PRIMARY KEY,
                    func_name TEXT,
                    trigger_type TEXT,
                    trigger_args TEXT,
                    last_run TEXT,
                    next_run TEXT,
                    status TEXT DEFAULT 'active'
                )
                """
            )
            conn.commit()

    def add_interval_job(
        self,
        func: Callable,
        minutes: int = 15,
        job_id: Optional[str] = None,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
    ) -> str:
        """
        Belirli aralikla calisacak gorev ekle.
        """
        jid = job_id or f"interval_{func.__name__}_{minutes}"
        if self._scheduler:
            trigger = IntervalTrigger(minutes=minutes)
            self._scheduler.add_job(
                func=func,
                trigger=trigger,
                id=jid,
                args=args or (),
                kwargs=kwargs or {},
                replace_existing=True,
            )
        self._jobs[jid] = {
            "func": func,
            "type": "interval",
            "minutes": minutes,
            "args": args or (),
            "kwargs": kwargs or {},
        }
        self._log_job(jid, func.__name__, "interval", {"minutes": minutes})
        return jid

    def add_daily_job(
        self,
        func: Callable,
        hour: int,
        minute: int = 0,
        job_id: Optional[str] = None,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
    ) -> str:
        """
        Her gun belirli saatte calisacak gorev ekle.
        """
        jid = job_id or f"daily_{func.__name__}_{hour:02d}{minute:02d}"
        if self._scheduler:
            trigger = CronTrigger(hour=hour, minute=minute)
            self._scheduler.add_job(
                func=func,
                trigger=trigger,
                id=jid,
                args=args or (),
                kwargs=kwargs or {},
                replace_existing=True,
            )
        self._jobs[jid] = {
            "func": func,
            "type": "daily",
            "hour": hour,
            "minute": minute,
            "args": args or (),
            "kwargs": kwargs or {},
        }
        self._log_job(jid, func.__name__, "daily", {"hour": hour, "minute": minute})
        return jid

    def remove_job(self, job_id: str) -> bool:
        if self._scheduler:
            try:
                self._scheduler.remove_job(job_id)
            except Exception:
                pass
        if job_id in self._jobs:
            del self._jobs[job_id]
            return True
        return False

    def start(self):
        if self._scheduler:
            self._scheduler.start()

    def shutdown(self):
        if self._scheduler:
            self._scheduler.shutdown(wait=False)

    def list_jobs(self) -> list[dict]:
        if self._scheduler:
            jobs = self._scheduler.get_jobs()
            return [
                {
                    "id": j.id,
                    "name": j.name,
                    "next_run": str(j.next_run_time) if j.next_run_time else None,
                }
                for j in jobs
            ]
        return [{"id": k, "type": v["type"]} for k, v in self._jobs.items()]

    def _log_job(self, job_id: str, func_name: str, trigger_type: str, trigger_args: dict):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO scheduled_tasks (id, func_name, trigger_type, trigger_args, status)
                VALUES (?, ?, ?, ?, 'active')
                """,
                (job_id, func_name, trigger_type, json.dumps(trigger_args)),
            )
            conn.commit()

    def get_task_log(self, limit: int = 50) -> list[dict]:
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "SELECT id, func_name, trigger_type, last_run, next_run, status FROM scheduled_tasks ORDER BY last_run DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()
        return [
            {
                "id": r[0],
                "func_name": r[1],
                "trigger_type": r[2],
                "last_run": r[3],
                "next_run": r[4],
                "status": r[5],
            }
            for r in rows
        ]

    def update_last_run(self, job_id: str):
        now = datetime.now().isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "UPDATE scheduled_tasks SET last_run = ? WHERE id = ?",
                (now, job_id),
            )
            conn.commit()


if __name__ == "__main__":
    def dummy():
        print("Task calisti:", datetime.now().isoformat())

    sched = TaskScheduler()
    sched.add_interval_job(dummy, minutes=1, job_id="demo_interval")
    sched.start()
    print("Scheduler basladi. Jobs:", sched.list_jobs())
    import time
    time.sleep(65)
    sched.shutdown()
