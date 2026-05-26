"""
.agents/progress_tracker.py — Gorev ilerleme takibi
"""
from datetime import datetime
from typing import Dict, List


class ProgressTracker:
    """
    Ajan gorevlerinin ilerleme durumunu takip eder.

    Durumlar: PENDING -> IN_PROGRESS -> REVIEW -> DONE / ROLLED_BACK

    K191: Her gorev durum degisikligi loglanir ve raporlanir.
    """

    def __init__(self):
        self.tasks: Dict[str, dict] = {}

    def create(self, task_id: str, title: str) -> None:
        self.tasks[task_id] = {
            "title": title,
            "status": "PENDING",
            "created": datetime.utcnow().isoformat(),
            "updated": datetime.utcnow().isoformat(),
            "logs": [],
        }

    def transition(self, task_id: str, new_status: str, note: str = "") -> None:
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = new_status
            self.tasks[task_id]["updated"] = datetime.utcnow().isoformat()
            self.tasks[task_id]["logs"].append({"status": new_status, "note": note})

    def report(self) -> List[dict]:
        return [
            {"id": k, **v}
            for k, v in sorted(self.tasks.items(), key=lambda x: x[1]["updated"], reverse=True)
        ]
