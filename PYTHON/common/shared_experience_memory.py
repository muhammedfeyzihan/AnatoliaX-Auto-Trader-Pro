"""
shared_experience_memory.py — Unified Cross-Agent Experience Memory

Bridges OpenClaw (agent routing) and Hermes (risk/skill) into a single
shared memory layer. All agent decisions, outcomes, and lessons are
persisted here for collective learning.

Usage:
    from common.shared_experience_memory import SharedExperienceMemory
    mem = SharedExperienceMemory()
    mem.record_experience(agent="signal", action="BUY THYAO", outcome=1.2, context={...})
    lesson = mem.query_lessons(symbol="THYAO", min_score=0.7)
"""

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from collections import defaultdict

_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

import numpy as np


@dataclass
class ExperienceRecord:
    agent: str
    action: str
    symbol: str
    outcome: float  # PnL or score
    context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    checksum: str = ""

    def __post_init__(self):
        if not self.checksum:
            payload = f"{self.agent}_{self.action}_{self.symbol}_{self.timestamp}"
            self.checksum = hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return asdict(self)


class SharedExperienceMemory:
    """
    Persistent shared memory for all agents (OpenClaw + Hermes + Strategy).

    Stores:
    - Every execution decision and its outcome
    - Risk gate blocks and reasons
    - Black swan events and system halts
    - Strategy registry reloads
    - Skill engine learnings

    Queryable by symbol, agent, tag, time window, outcome threshold.
    """

    def __init__(self, db_path: Optional[str] = None, max_records: int = 100_000):
        self._db_path = db_path or os.path.join(
            os.path.dirname(__file__), "..", "memory", "shared_experience.jsonl"
        )
        self._max_records = max_records
        self._records: List[ExperienceRecord] = []
        self._symbol_index: Dict[str, List[int]] = defaultdict(list)
        self._agent_index: Dict[str, List[int]] = defaultdict(list)
        self._tag_index: Dict[str, List[int]] = defaultdict(list)
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _load(self):
        path = Path(self._db_path)
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    rec = ExperienceRecord(**data)
                    self._index_record(rec, len(self._records))
                    self._records.append(rec)
        except Exception:
            pass

    def _save(self):
        path = Path(self._db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for rec in self._records:
                f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")

    def _index_record(self, rec: ExperienceRecord, idx: int):
        self._symbol_index[rec.symbol.upper()].append(idx)
        self._agent_index[rec.agent].append(idx)
        for tag in rec.tags:
            self._tag_index[tag].append(idx)

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------
    def record_experience(
        self,
        agent: str,
        action: str,
        symbol: str,
        outcome: float,
        context: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
    ) -> ExperienceRecord:
        rec = ExperienceRecord(
            agent=agent,
            action=action,
            symbol=symbol,
            outcome=outcome,
            context=context or {},
            tags=tags or [],
        )
        self._index_record(rec, len(self._records))
        self._records.append(rec)
        # Trim if over limit
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records:]
            self._rebuild_indices()
        self._save()
        return rec

    def record_block(
        self,
        agent: str,
        symbol: str,
        reason: str,
        context: Optional[Dict] = None,
    ) -> ExperienceRecord:
        return self.record_experience(
            agent=agent,
            action=f"BLOCKED: {reason}",
            symbol=symbol,
            outcome=0.0,
            context=context,
            tags=["block", agent, symbol.upper()],
        )

    def record_black_swan(
        self,
        symbol: str,
        level: str,
        reason: str,
        context: Optional[Dict] = None,
    ) -> ExperienceRecord:
        return self.record_experience(
            agent="black_swan_guard",
            action=f"BLACK_SWAN_{level}: {reason}",
            symbol=symbol,
            outcome=-999.0,
            context=context,
            tags=["black_swan", level, symbol.upper()],
        )

    def record_strategy_reload(
        self,
        symbol: str,
        old_version: str,
        new_version: str,
        status: str,
    ) -> ExperienceRecord:
        return self.record_experience(
            agent="strategy_registry",
            action=f"RELOAD_{status}: {old_version} -> {new_version}",
            symbol=symbol,
            outcome=0.0,
            context={"old_version": old_version, "new_version": new_version, "status": status},
            tags=["strategy_reload", status, symbol.upper()],
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def query(
        self,
        symbol: Optional[str] = None,
        agent: Optional[str] = None,
        tag: Optional[str] = None,
        min_outcome: Optional[float] = None,
        max_age_seconds: Optional[float] = None,
        limit: int = 100,
    ) -> List[ExperienceRecord]:
        candidates = set(range(len(self._records)))
        if symbol:
            candidates &= set(self._symbol_index.get(symbol.upper(), []))
        if agent:
            candidates &= set(self._agent_index.get(agent, []))
        if tag:
            candidates &= set(self._tag_index.get(tag, []))

        now = time.time()
        results = []
        for idx in sorted(candidates, reverse=True):
            rec = self._records[idx]
            if min_outcome is not None and rec.outcome < min_outcome:
                continue
            if max_age_seconds is not None and (now - rec.timestamp) > max_age_seconds:
                continue
            results.append(rec)
            if len(results) >= limit:
                break
        return results

    def query_lessons(
        self,
        symbol: str,
        min_score: float = 0.5,
        lookback_days: int = 30,
    ) -> List[dict]:
        """Return actionable lessons from past experiences for a symbol."""
        max_age = lookback_days * 86400
        recs = self.query(symbol=symbol, max_age_seconds=max_age, limit=1000)
        if not recs:
            return []

        wins = [r for r in recs if r.outcome > 0]
        losses = [r for r in recs if r.outcome < 0]
        blocks = [r for r in recs if "block" in r.tags]

        lessons = []
        if losses:
            avg_loss = np.mean([r.outcome for r in losses])
            common_reasons = defaultdict(int)
            for r in losses:
                reason = r.context.get("reason", r.action)
                common_reasons[reason] += 1
            top_reason = max(common_reasons, key=common_reasons.get) if common_reasons else "unknown"
            lessons.append({
                "type": "avoid",
                "symbol": symbol,
                "avg_loss": round(float(avg_loss), 2),
                "top_reason": top_reason,
                "frequency": len(losses),
                "confidence": round(len(losses) / len(recs), 2),
            })

        if wins:
            avg_win = np.mean([r.outcome for r in wins])
            lessons.append({
                "type": "repeat",
                "symbol": symbol,
                "avg_win": round(float(avg_win), 2),
                "frequency": len(wins),
                "confidence": round(len(wins) / len(recs), 2),
            })

        if blocks:
            block_reasons = defaultdict(int)
            for r in blocks:
                block_reasons[r.context.get("reason", r.action)] += 1
            lessons.append({
                "type": "block_pattern",
                "symbol": symbol,
                "top_block_reason": max(block_reasons, key=block_reasons.get),
                "block_count": len(blocks),
            })

        return [l for l in lessons if l.get("confidence", 1.0) >= min_score]

    def get_agent_performance(self, agent: str, lookback_days: int = 30) -> dict:
        """Win rate, avg outcome, and trend for an agent."""
        recs = self.query(agent=agent, max_age_seconds=lookback_days * 86400, limit=10_000)
        if not recs:
            return {"agent": agent, "records": 0, "win_rate": 0.0, "avg_outcome": 0.0}
        outcomes = [r.outcome for r in recs if r.outcome != 0 and r.outcome != -999.0]
        wins = sum(1 for o in outcomes if o > 0)
        return {
            "agent": agent,
            "records": len(recs),
            "win_rate": round(wins / len(outcomes), 3) if outcomes else 0.0,
            "avg_outcome": round(float(np.mean(outcomes)), 3) if outcomes else 0.0,
            "total_pnl": round(float(np.sum(outcomes)), 2) if outcomes else 0.0,
        }

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------
    def _rebuild_indices(self):
        self._symbol_index.clear()
        self._agent_index.clear()
        self._tag_index.clear()
        for idx, rec in enumerate(self._records):
            self._index_record(rec, idx)

    def stats(self) -> dict:
        return {
            "total_records": len(self._records),
            "unique_symbols": len(self._symbol_index),
            "unique_agents": len(self._agent_index),
            "unique_tags": len(self._tag_index),
            "db_path": self._db_path,
        }
    
    def count(self) -> int:
        """Return the number of experience records."""
        return len(self._records)

    def reset(self):
        self._records.clear()
        self._symbol_index.clear()
        self._agent_index.clear()
        self._tag_index.clear()
        self._save()


if __name__ == "__main__":
    mem = SharedExperienceMemory()
    mem.record_experience("signal", "BUY THYAO", "THYAO", 2.5, {"confidence": 85})
    mem.record_experience("risk", "BLOCKED: spread too wide", "THYAO", 0.0, {"spread": 1.2}, tags=["block"])
    print(mem.stats())
    print(mem.query_lessons("THYAO"))
    print(mem.get_agent_performance("signal"))
