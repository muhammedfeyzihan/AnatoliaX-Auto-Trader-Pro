"""
skill_engine.py — Self-Improving Skill System
Inspired by Hermes Agent's autonomous skill creation from experience.

Skills are small, reusable units of knowledge learned from trade outcomes.
The engine auto-creates skills after complex tasks and refines them over time.

Usage:
    from hermes_adapter.skill_engine import SkillEngine
    engine = SkillEngine()
    engine.learn(symbol="THYAO", setup="ema_cross", outcome="win", pnl=500)
    skill = engine.get_best_skill("THYAO")
"""

import json
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

SKILLS_DIR = Path("data/skills")
SKILLS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Skill:
    skill_id: str
    name: str
    setup: str  # e.g., "ema_cross", "vwap_deviation"
    symbols: List[str] = field(default_factory=list)
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    avg_pnl: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used: str = ""
    confidence: float = 0.0  # 0-100

    def record(self, pnl: float):
        if pnl > 0:
            self.wins += 1
        else:
            self.losses += 1
        self.total_pnl += pnl
        self._update_stats()
        self.last_used = datetime.now().isoformat()

    def _update_stats(self):
        total = self.wins + self.losses
        self.win_rate = self.wins / total if total > 0 else 0.0
        self.avg_pnl = self.total_pnl / total if total > 0 else 0.0
        # Confidence rises with sample size (Wilson score lower bound approx)
        self.confidence = self.win_rate * 100 * min(1.0, total / 10.0)

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "setup": self.setup,
            "symbols": self.symbols,
            "wins": self.wins,
            "losses": self.losses,
            "total_pnl": self.total_pnl,
            "win_rate": round(self.win_rate, 3),
            "avg_pnl": round(self.avg_pnl, 3),
            "created_at": self.created_at,
            "last_used": self.last_used,
            "confidence": round(self.confidence, 1),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Skill":
        s = cls(
            skill_id=d["skill_id"],
            name=d["name"],
            setup=d["setup"],
            symbols=d.get("symbols", []),
            wins=d.get("wins", 0),
            losses=d.get("losses", 0),
            total_pnl=d.get("total_pnl", 0.0),
            created_at=d.get("created_at", datetime.now().isoformat()),
            last_used=d.get("last_used", ""),
        )
        s._update_stats()
        return s


class SkillEngine:
    """
    Manages skill creation, learning, and retrieval.
    Persists skills to JSONL files.
    """

    def __init__(self, skills_dir: Path = SKILLS_DIR):
        self.skills_dir = skills_dir
        self._skills: Dict[str, Skill] = {}
        self._load_all()

    def _make_id(self, setup: str, symbol: str = "") -> str:
        raw = f"{setup}_{symbol}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _load_all(self):
        if not self.skills_dir.exists():
            return
        for fpath in self.skills_dir.glob("*.jsonl"):
            with open(fpath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        skill = Skill.from_dict(data)
                        self._skills[skill.skill_id] = skill
                    except Exception:
                        continue

    def _save_skill(self, skill: Skill):
        fpath = self.skills_dir / f"{skill.setup}.jsonl"
        # Append-only
        with open(fpath, "a", encoding="utf-8") as f:
            f.write(json.dumps(skill.to_dict(), ensure_ascii=False) + "\n")

    def learn(self, symbol: str, setup: str, outcome: str, pnl: float):
        """Record a trade outcome for a setup."""
        sid = self._make_id(setup, symbol)
        skill = self._skills.get(sid)
        if skill is None:
            skill = Skill(
                skill_id=sid,
                name=f"{setup}_{symbol}",
                setup=setup,
                symbols=[symbol],
            )
            self._skills[sid] = skill
        if symbol not in skill.symbols:
            skill.symbols.append(symbol)
        skill.record(pnl)
        self._save_skill(skill)

    def get_best_skill(self, symbol: str, min_confidence: float = 50.0) -> Optional[Skill]:
        """Return the highest-confidence skill for a symbol."""
        candidates = [
            s for s in self._skills.values()
            if symbol in s.symbols and s.confidence >= min_confidence
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda s: s.confidence)

    def list_skills(self, setup: Optional[str] = None) -> List[Skill]:
        skills = list(self._skills.values())
        if setup:
            skills = [s for s in skills if s.setup == setup]
        return sorted(skills, key=lambda s: s.confidence, reverse=True)

    def get_skill_stats(self) -> dict:
        total = len(self._skills)
        wins = sum(s.wins for s in self._skills.values())
        losses = sum(s.losses for s in self._skills.values())
        return {
            "total_skills": total,
            "total_wins": wins,
            "total_losses": losses,
            "win_rate": wins / (wins + losses) if (wins + losses) > 0 else 0.0,
        }
