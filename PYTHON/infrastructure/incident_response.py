"""
infrastructure/incident_response.py — Autonomous Incident Response (Phase 2)
Module 22 from anatoliax_prompt_v6.txt

Features:
  - Self-healing rules:
      IF feed_corruption_detected THEN switch_to_backup_feed
      IF kafka_lag > threshold THEN scale_consumers_by(factor=2)
      IF memory_usage > 0.8*max THEN graceful_restart(component)
      IF broker_health_check = 0 THEN failover_to_backup + alert
  - Structured incident logging with post-mortem template.
"""

import json
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable


@dataclass
class Incident:
    incident_id: str
    timestamp: str
    severity: str
    rule_triggered: str
    action_taken: str
    resolution_time_sec: Optional[float] = None


class AutonomousIncidentResponse:
    """
    Self-healing engine with rule-based incident response.
    """

    def __init__(self, db_path: str = "incidents.db"):
        self.db_path = db_path
        self._rules: Dict[str, Callable] = {}
        self._incidents: List[Incident] = []
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    severity TEXT,
                    rule TEXT,
                    action TEXT,
                    resolution_time REAL
                )
            """)
            conn.commit()

    def register_rule(self, name: str, condition: Callable[[], bool], action: Callable):
        self._rules[name] = {"condition": condition, "action": action}

    def evaluate(self):
        for name, rule in self._rules.items():
            try:
                if rule["condition"]():
                    start = time.time()
                    rule["action"]()
                    elapsed = time.time() - start
                    self._log_incident(name, "auto", elapsed)
            except Exception as e:
                self._log_incident(name, "error", None, str(e))

    def _log_incident(self, rule: str, severity: str, resolution_time: Optional[float], error: str = ""):
        inc = Incident(
            incident_id=f"INC-{int(time.time()*1000)}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            severity=severity,
            rule_triggered=rule,
            action_taken=error or "executed",
            resolution_time_sec=resolution_time,
        )
        self._incidents.append(inc)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO incidents (id, timestamp, severity, rule, action, resolution_time) VALUES (?, ?, ?, ?, ?, ?)",
                (inc.incident_id, inc.timestamp, inc.severity, inc.rule_triggered, inc.action_taken, inc.resolution_time_sec)
            )
            conn.commit()

    def generate_post_mortem(self, incident_id: str) -> Optional[Dict]:
        for inc in self._incidents:
            if inc.incident_id == incident_id:
                return {
                    "incident_id": inc.incident_id,
                    "timestamp": inc.timestamp,
                    "severity": inc.severity,
                    "root_cause": inc.rule_triggered,
                    "action_taken": inc.action_taken,
                    "resolution_time_sec": inc.resolution_time_sec,
                    "prevention": "Review and tune thresholds",
                }
        return None
