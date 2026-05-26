"""
agent_trust_scorer.py — Ruflo-Inspired Agent Trust Scoring

Scores each AI agent using a weighted formula:
    Trust = 0.4 * success_rate + 0.2 * uptime_ratio + 0.2 * threat_score + 0.2 * integrity_score

Agents with low trust are flagged as Byzantine (potentially faulty/malicious).
Inspired by Ruflo's federation gateway peer scoring.

Usage:
    scorer = AgentTrustScorer()
    scorer.record_prediction(agent="signal", symbol="THYAO", expected=105, actual=103)
    score = scorer.get_trust("signal")
    if score < 50:
        print("Byzantine agent detected!")
"""

import json
import hashlib
from dataclasses import dataclass, field
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime, timedelta

TRUST_DIR = Path("data/trust")
TRUST_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class AgentRecord:
    agent_id: str
    predictions: int = 0
    correct: int = 0
    total_pnl: float = 0.0
    first_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active: str = ""
    threat_count: int = 0  # Manipulation alerts triggered by this agent
    integrity_violations: int = 0  # Rule violations

    @property
    def success_rate(self) -> float:
        return self.correct / self.predictions if self.predictions > 0 else 0.5

    @property
    def uptime_ratio(self) -> float:
        """Active within last 7 days / total days since first seen."""
        try:
            first = datetime.fromisoformat(self.first_seen)
            last = datetime.fromisoformat(self.last_active) if self.last_active else first
            total_days = max(1, (datetime.now() - first).days)
            active_days = max(1, (last - first).days + 1)
            return min(1.0, active_days / total_days)
        except Exception:
            return 1.0

    @property
    def threat_score(self) -> float:
        """Normalized threat count: fewer threats = higher score."""
        return max(0.0, 1.0 - (self.threat_count / max(1, self.predictions)) * 5)

    @property
    def integrity_score(self) -> float:
        """Normalized integrity violations."""
        return max(0.0, 1.0 - (self.integrity_violations / max(1, self.predictions)) * 5)

    @property
    def trust_score(self) -> float:
        """Ruflo formula: 0.4*success + 0.2*uptime + 0.2*threat + 0.2*integrity."""
        return (
            0.4 * self.success_rate +
            0.2 * self.uptime_ratio +
            0.2 * self.threat_score +
            0.2 * self.integrity_score
        ) * 100

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "predictions": self.predictions,
            "correct": self.correct,
            "total_pnl": self.total_pnl,
            "first_seen": self.first_seen,
            "last_active": self.last_active,
            "threat_count": self.threat_count,
            "integrity_violations": self.integrity_violations,
            "trust_score": round(self.trust_score, 2),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AgentRecord":
        r = cls(agent_id=d["agent_id"])
        r.predictions = d.get("predictions", 0)
        r.correct = d.get("correct", 0)
        r.total_pnl = d.get("total_pnl", 0.0)
        r.first_seen = d.get("first_seen", datetime.now().isoformat())
        r.last_active = d.get("last_active", "")
        r.threat_count = d.get("threat_count", 0)
        r.integrity_violations = d.get("integrity_violations", 0)
        return r


class AgentTrustScorer:
    """
    Tracks and scores agent trustworthiness.
    Byzantine detection: agents with trust < threshold are flagged.
    """

    def __init__(self, byzantine_threshold: float = 50.0, trust_dir: Path = TRUST_DIR):
        self.byzantine_threshold = byzantine_threshold
        self.trust_dir = trust_dir
        self._records: Dict[str, AgentRecord] = {}
        self._load_all()

    def _file_path(self, agent_id: str) -> Path:
        return self.trust_dir / f"{agent_id}.json"

    def _load_all(self):
        if not self.trust_dir.exists():
            return
        for fpath in self.trust_dir.glob("*.json"):
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                rec = AgentRecord.from_dict(data)
                self._records[rec.agent_id] = rec
            except Exception:
                continue

    def _save(self, rec: AgentRecord):
        fpath = self._file_path(rec.agent_id)
        fpath.write_text(json.dumps(rec.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def record_prediction(self, agent_id: str, symbol: str, expected: float, actual: float,
                          tolerance_pct: float = 0.03):
        """Record a prediction outcome."""
        rec = self._records.get(agent_id)
        if rec is None:
            rec = AgentRecord(agent_id=agent_id)
            self._records[agent_id] = rec

        rec.predictions += 1
        deviation = abs(expected - actual) / expected if expected != 0 else 1.0
        if deviation <= tolerance_pct:
            rec.correct += 1

        rec.last_active = datetime.now().isoformat()
        self._save(rec)

    def record_threat(self, agent_id: str, symbol: str):
        """Record that this agent triggered a manipulation alert."""
        rec = self._records.get(agent_id)
        if rec is None:
            rec = AgentRecord(agent_id=agent_id)
            self._records[agent_id] = rec
        rec.threat_count += 1
        self._save(rec)

    def record_integrity_violation(self, agent_id: str, reason: str):
        """Record a rule violation (e.g., unauthorized trade)."""
        rec = self._records.get(agent_id)
        if rec is None:
            rec = AgentRecord(agent_id=agent_id)
            self._records[agent_id] = rec
        rec.integrity_violations += 1
        rec.last_active = datetime.now().isoformat()
        self._save(rec)

    def get_trust(self, agent_id: str) -> float:
        rec = self._records.get(agent_id)
        if rec is None:
            return 50.0  # Neutral default
        return rec.trust_score

    def is_byzantine(self, agent_id: str) -> bool:
        return self.get_trust(agent_id) < self.byzantine_threshold

    def get_all_scores(self) -> Dict[str, dict]:
        return {aid: rec.to_dict() for aid, rec in self._records.items()}

    def get_top_agents(self, n: int = 5) -> list[dict]:
        sorted_agents = sorted(self._records.values(), key=lambda r: r.trust_score, reverse=True)
        return [r.to_dict() for r in sorted_agents[:n]]

    def reset_agent(self, agent_id: str):
        if agent_id in self._records:
            del self._records[agent_id]
            fpath = self._file_path(agent_id)
            if fpath.exists():
                fpath.unlink()
