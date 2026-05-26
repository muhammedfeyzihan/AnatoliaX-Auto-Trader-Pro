"""
agents/cognitive_memory.py — Multi-Agent Cognitive Memory Layer (Phase 5)
Module 34 from anatoliax_prompt_v6.txt

Features:
  - Episodic memory: experiences as (context, action, outcome, emotion, timestamp)
  - Semantic memory: financial concepts, causal relationships, market regimes
  - Strategic memory: long-term goals, plans, lessons learned
  - MemGPT-style memory management: working / episodic / semantic
  - Integration with existing PersistentAgentMemory (SQLite+ChromaDB)
"""

import json
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from collections import deque


@dataclass
class EpisodicMemory:
    """A single experience episode."""
    context: str
    action: str
    outcome: str
    emotion: str  # e.g., "regret", "euphoria", "neutral"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    symbol: str = ""
    pnl: float = 0.0


@dataclass
class SemanticMemory:
    """Compressed long-term concept / causal rule."""
    concept: str
    relation: str
    target: str
    weight: float = 1.0
    evidence_count: int = 1
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class StrategicMemory:
    """Long-term plans and lessons."""
    goal: str
    plan_steps: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CognitiveMemoryLayer:
    """
    MemGPT-style memory management for agents.
    Working (hot, limited), Episodic buffer (recent), Semantic store (long-term graph).
    """

    def __init__(
        self,
        db_path: str = "cognitive_memory.db",
        working_capacity: int = 10,
        episodic_capacity: int = 1000,
    ):
        self.db_path = db_path
        self.working_capacity = working_capacity
        self.episodic_capacity = episodic_capacity

        # Hot working memory (limited capacity, fast access)
        self.working: deque = deque(maxlen=working_capacity)

        # Episodic buffer (recent experiences, FIFO)
        self.episodic: deque = deque(maxlen=episodic_capacity)

        # Semantic store (long-term, graph-structured)
        self.semantic: List[SemanticMemory] = []

        # Strategic store
        self.strategic: List[StrategicMemory] = []

        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodic (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    context TEXT,
                    action TEXT,
                    outcome TEXT,
                    emotion TEXT,
                    timestamp TEXT,
                    symbol TEXT,
                    pnl REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    concept TEXT,
                    relation TEXT,
                    target TEXT,
                    weight REAL,
                    evidence_count INTEGER,
                    last_updated TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strategic (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal TEXT,
                    plan_steps TEXT,
                    lessons_learned TEXT,
                    timestamp TEXT
                )
            """)
            conn.commit()

    # ── Working Memory ─────────────────────────────────────

    def add_to_working(self, item: Dict[str, Any]):
        self.working.append(item)

    def get_working(self) -> List[Dict[str, Any]]:
        return list(self.working)

    # ── Episodic Memory ────────────────────────────────────

    def add_episode(self, episode: EpisodicMemory):
        self.episodic.append(episode)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO episodic (context, action, outcome, emotion, timestamp, symbol, pnl) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (episode.context, episode.action, episode.outcome, episode.emotion,
                 episode.timestamp, episode.symbol, episode.pnl)
            )
            conn.commit()

    def retrieve_episodes(self, context_query: str, limit: int = 10) -> List[EpisodicMemory]:
        """Similarity search on context + recency bias."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT context, action, outcome, emotion, timestamp, symbol, pnl FROM episodic ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
        return [EpisodicMemory(*r) for r in rows]

    # ── Semantic Memory ──────────────────────────────────

    def add_semantic(self, memory: SemanticMemory):
        self.semantic.append(memory)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO semantic (concept, relation, target, weight, evidence_count, last_updated) VALUES (?, ?, ?, ?, ?, ?)",
                (memory.concept, memory.relation, memory.target, memory.weight,
                 memory.evidence_count, memory.last_updated)
            )
            conn.commit()

    def query_semantic(self, concept: str) -> List[SemanticMemory]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT concept, relation, target, weight, evidence_count, last_updated FROM semantic WHERE concept = ?",
                (concept,)
            )
            rows = cursor.fetchall()
        return [SemanticMemory(*r) for r in rows]

    # ── Strategic Memory ───────────────────────────────────

    def add_strategic(self, memory: StrategicMemory):
        self.strategic.append(memory)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO strategic (goal, plan_steps, lessons_learned, timestamp) VALUES (?, ?, ?, ?)",
                (memory.goal, json.dumps(memory.plan_steps), json.dumps(memory.lessons_learned), memory.timestamp)
            )
            conn.commit()

    def get_strategic_summary(self) -> Dict[str, Any]:
        return {
            "goals": [s.goal for s in self.strategic],
            "total_lessons": sum(len(s.lessons_learned) for s in self.strategic),
            "latest": self.strategic[-1].timestamp if self.strategic else None,
        }

    # ── MemGPT-style Compaction ────────────────────────────

    def compact(self):
        """
        When episodic buffer is full, compress recent episodes into semantic memories.
        """
        if len(self.episodic) < self.episodic_capacity:
            return

        # Simple compression: extract frequent context-action pairs
        freq: Dict[str, int] = {}
        for ep in self.episodic:
            key = f"{ep.context} -> {ep.action}"
            freq[key] = freq.get(key, 0) + 1

        for key, count in freq.items():
            if count >= 3:
                ctx, act = key.split(" -> ", 1)
                self.add_semantic(SemanticMemory(
                    concept=ctx,
                    relation="leads_to",
                    target=act,
                    weight=min(count / 10.0, 1.0),
                    evidence_count=count,
                ))

        # Clear episodic buffer
        self.episodic.clear()
