"""
task_queue.py — SQLite tabanli gorev kuyrugu
"""
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class Task:
    id: int
    agent: str
    description: str
    status: str
    priority: int
    created_at: str


class TaskQueue:
    """
    SQLite tabanli gorev kuyrugu.

    Ozellikler:
    - Oncelik sirali kuyruk
    - Ajan bazli filtreleme
    - Durum gecisleri: pending -> in_progress -> completed / failed
    """

    def __init__(self, db_path: str = ".agents/task_queue.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT,
                description TEXT,
                status TEXT DEFAULT 'pending',
                priority INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def enqueue(self, agent: str, description: str, priority: int = 0) -> int:
        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(self.db_path)
        cur = conn.execute(
            "INSERT INTO queue (agent, description, priority, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (agent, description, priority, now, now),
        )
        conn.commit()
        task_id = cur.lastrowid
        conn.close()
        return task_id

    def dequeue(self, agent: Optional[str] = None) -> Optional[Task]:
        conn = sqlite3.connect(self.db_path)
        if agent:
            row = conn.execute(
                "SELECT * FROM queue WHERE agent = ? AND status = 'pending' ORDER BY priority DESC, id ASC LIMIT 1",
                (agent,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM queue WHERE status = 'pending' ORDER BY priority DESC, id ASC LIMIT 1"
            ).fetchone()
        if not row:
            conn.close()
            return None
        task = Task(*row)
        conn.execute("UPDATE queue SET status = 'in_progress', updated_at = ? WHERE id = ?",
                     (datetime.now(timezone.utc).isoformat(), task.id))
        conn.commit()
        conn.close()
        return task

    def complete(self, task_id: int) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute("UPDATE queue SET status = 'completed', updated_at = ? WHERE id = ?",
                     (datetime.now(timezone.utc).isoformat(), task_id))
        conn.commit()
        conn.close()

    def fail(self, task_id: int) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute("UPDATE queue SET status = 'failed', updated_at = ? WHERE id = ?",
                     (datetime.now(timezone.utc).isoformat(), task_id))
        conn.commit()
        conn.close()
