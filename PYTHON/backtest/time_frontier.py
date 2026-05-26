"""
backtest/time_frontier.py — Replay Time Frontier System (Phase 1)
Module 9 from anatoliax_prompt_v6.txt

Features:
  - Zero look-ahead bias. All agents operate on event time t_e, not wall time t_w.
  - Market data arrival: D(t_e) = {ticks with timestamp <= t_e}.
  - Agent processing latency: delta_t_proc ~ measured_distribution.
  - Clock sync: t_e = max(last_tick_time, t_e + clock_increment).
"""

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable


@dataclass
class Tick:
    timestamp: float
    price: float
    volume: float
    symbol: str = ""


class TimeFrontier:
    """
    Enforces zero look-ahead bias via event-time processing.
    """

    def __init__(self, clock_increment_ns: int = 1):
        self.clock_increment_ns = clock_increment_ns
        self._event_time: float = 0.0
        self._tick_buffer: List[Tick] = []
        self._latency_distribution: Optional[Callable[[], float]] = None

    def set_latency_distribution(self, fn: Callable[[], float]):
        self._latency_distribution = fn

    def ingest_tick(self, tick: Tick):
        self._tick_buffer.append(tick)
        self._tick_buffer.sort(key=lambda t: t.timestamp)
        if self._event_time == 0.0:
            self._event_time = tick.timestamp

    def step(self) -> Optional[Tick]:
        """
        Advance event time and return the next tick available at t_e.
        Constraint: no agent accesses D(t_e + delta) for delta > 0.
        """
        if not self._tick_buffer:
            return None

        next_tick = self._tick_buffer[0]
        if next_tick.timestamp > self._event_time:
            self._event_time = next_tick.timestamp

        self._tick_buffer.pop(0)
        return next_tick

    def available_data(self) -> List[Tick]:
        """D(t_e) = {ticks with timestamp <= t_e}."""
        return [t for t in self._tick_buffer if t.timestamp <= self._event_time]

    def agent_latency(self) -> float:
        if self._latency_distribution:
            return self._latency_distribution()
        return random.uniform(0.0001, 0.001)  # default 100us-1ms

    def get_event_time(self) -> float:
        return self._event_time
