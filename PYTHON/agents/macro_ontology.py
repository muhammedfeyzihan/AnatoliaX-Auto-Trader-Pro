"""
agents/macro_ontology.py — Global Macro Ontology Engine (Phase 4)
Module 25 from anatoliax_prompt_v6.txt

Features:
  - Knowledge graph G = (V, E, W)
  - Vertices: entities {Fed, ECB, OPEC, BIST, SPX, USDTRY, BRENT, VIX, ...}
  - Edges: causal relationships with weight w = correlation_strength, time_lag tau
  - Inference: P(impact_on_asset | e) = sum(path w_path)
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque


@dataclass
class CausalEdge:
    source: str
    target: str
    weight: float
    time_lag_days: float
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MacroOntologyEngine:
    """
    Knowledge graph for global macro causal relationships.
    """

    def __init__(self, db_path: str = "macro_ontology.db"):
        self.db_path = db_path
        self._vertices: set = set()
        self._edges: List[CausalEdge] = []
        self._adj: Dict[str, List[CausalEdge]] = defaultdict(list)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    source TEXT,
                    target TEXT,
                    weight REAL,
                    lag REAL,
                    updated TEXT,
                    PRIMARY KEY (source, target)
                )
            """)
            conn.commit()
        self._load_edges()

    def _load_edges(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT source, target, weight, lag, updated FROM edges")
            for row in cursor.fetchall():
                edge = CausalEdge(*row)
                self._edges.append(edge)
                self._vertices.update([edge.source, edge.target])
                self._adj[edge.source].append(edge)

    def add_edge(self, source: str, target: str, weight: float, time_lag_days: float):
        edge = CausalEdge(source, target, weight, time_lag_days)
        self._edges.append(edge)
        self._vertices.update([source, target])
        self._adj[source].append(edge)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO edges (source, target, weight, lag, updated) VALUES (?, ?, ?, ?, ?)",
                (source, target, weight, time_lag_days, edge.last_updated)
            )
            conn.commit()

    def infer_impact(self, event_entity: str, target_asset: str, max_hops: int = 3) -> float:
        """
        Propagate through graph and compute P(impact_on_asset | e) = sum(path w_path).
        """
        total = 0.0
        visited = set()
        queue = deque([(event_entity, 1.0, 0)])

        while queue:
            current, prob, hops = queue.popleft()
            if hops > max_hops:
                continue
            if current == target_asset and hops > 0:
                total += prob
                continue
            for edge in self._adj.get(current, []):
                key = (current, edge.target)
                if key not in visited:
                    visited.add(key)
                    queue.append((edge.target, prob * edge.weight, hops + 1))

        return min(total, 1.0)

    def get_causal_paths(self, event_entity: str, target_asset: str, max_hops: int = 3) -> List[List[str]]:
        paths = []
        queue = deque([(event_entity, [event_entity])])
        while queue:
            current, path = queue.popleft()
            if len(path) > max_hops + 1:
                continue
            if current == target_asset and len(path) > 1:
                paths.append(path)
                continue
            for edge in self._adj.get(current, []):
                if edge.target not in path:
                    queue.append((edge.target, path + [edge.target]))
        return paths
