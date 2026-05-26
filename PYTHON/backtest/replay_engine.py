"""
replay_engine.py — Deterministic tick-by-tick market replay.
K229: DeterministicReplayEngine.
"""
import csv
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Iterator
from datetime import datetime, timezone


@dataclass
class Tick:
    symbol: str = ""
    timestamp: Optional[datetime] = None
    price: float = 0.0
    size: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    volume: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)


class DeterministicReplayEngine:
    """
    Deterministik tick replay motoru.
    Ayni kaynak dosya + seed = ayni sonuc.
    """

    def __init__(self, seed: int = 42, speed: float = 1.0):
        self.seed = seed
        self.speed = speed
        self._ticks: List[Tick] = []
        self._index = 0
        self._handlers: List[Callable] = []
        self._running = False

    def load_csv(self, path: str, timestamp_col: str = "timestamp", price_col: str = "price"):
        self._ticks.clear()
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts = None
                if timestamp_col in row:
                    try:
                        ts = datetime.fromisoformat(row[timestamp_col].replace("Z", "+00:00"))
                    except Exception:
                        pass
                tick = Tick(
                    symbol=row.get("symbol", ""),
                    timestamp=ts,
                    price=float(row.get(price_col, 0)),
                    size=float(row.get("size", 0)),
                    bid=float(row.get("bid", 0)) if "bid" in row else float(row.get(price_col, 0)),
                    ask=float(row.get("ask", 0)) if "ask" in row else float(row.get(price_col, 0)),
                    volume=float(row.get("volume", 0)),
                )
                self._ticks.append(tick)

    def load_df(self, df, symbol: str = ""):
        self._ticks.clear()
        for _, row in df.iterrows():
            ts = row.get("timestamp")
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except Exception:
                    ts = None
            tick = Tick(
                symbol=symbol or row.get("symbol", ""),
                timestamp=ts,
                price=float(row.get("close", row.get("price", 0))),
                size=float(row.get("size", 0)),
                bid=float(row.get("bid", row.get("close", row.get("price", 0)))),
                ask=float(row.get("ask", row.get("close", row.get("price", 0)))),
                volume=float(row.get("volume", 0)),
            )
            self._ticks.append(tick)

    def add_handler(self, handler: Callable):
        self._handlers.append(handler)

    def step(self) -> Optional[Tick]:
        if self._index >= len(self._ticks):
            return None
        tick = self._ticks[self._index]
        self._index += 1
        for h in self._handlers:
            h(tick)
        return tick

    def run(self, max_ticks: Optional[int] = None):
        self._running = True
        count = 0
        while self._running and self._index < len(self._ticks):
            self.step()
            count += 1
            if max_ticks and count >= max_ticks:
                break
        self._running = False
        return count

    def reset(self):
        self._index = 0
        self._running = False

    def get_progress(self) -> Dict:
        total = len(self._ticks)
        return {
            "current": self._index,
            "total": total,
            "pct": self._index / total if total else 0.0,
        }

    def slice(self, start: int, end: int) -> List[Tick]:
        return self._ticks[start:end]

    def __iter__(self) -> Iterator[Tick]:
        for tick in self._ticks:
            yield tick
