"""
infrastructure/colocation.py — Exchange Co-Location Intelligence (Phase 5)
Module 31 from anatoliax_prompt_v6.txt

Features:
  - Ping heatmap: RTT_matrix[i,j] = round_trip_time(exchange_i, region_j)
  - Fiber route intelligence: known submarine cable paths
  - Region-aware execution: route through best POP
  - Auto-detect: if RTT > 1.5*baseline, trigger route investigation
"""

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from collections import defaultdict


class ColocationIntelligence:
    """
    Network topology awareness for execution routing.
    """

    def __init__(self):
        self._rtt_matrix: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._baselines: Dict[str, float] = {}

    def measure_rtt(self, exchange: str, region: str, rtt_ms: float):
        self._rtt_matrix[exchange][region] = rtt_ms
        if exchange not in self._baselines:
            self._baselines[exchange] = rtt_ms
        else:
            # EWMA update
            self._baselines[exchange] = 0.9 * self._baselines[exchange] + 0.1 * rtt_ms

    def best_region(self, exchange: str) -> str:
        regions = self._rtt_matrix.get(exchange, {})
        if not regions:
            return "unknown"
        return min(regions, key=regions.get)

    def route_investigation(self, exchange: str, current_rtt: float) -> Optional[Dict]:
        baseline = self._baselines.get(exchange, current_rtt)
        if current_rtt > 1.5 * baseline:
            return {
                "alert": True,
                "exchange": exchange,
                "current_rtt": current_rtt,
                "baseline": baseline,
                "suggestion": f"Investigate route to {exchange}. Consider failover.",
            }
        return None

    def get_heatmap(self) -> Dict:
        return dict(self._rtt_matrix)
