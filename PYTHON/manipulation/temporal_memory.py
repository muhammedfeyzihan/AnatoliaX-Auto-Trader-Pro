"""
temporal_memory.py — MiroFish-Inspired Dynamic Temporal Memory

Ingests seeds (macro events, news, KAP announcements) into a time-aware
memory graph. Agents query temporal context to enrich predictions.
Inspired by MiroFish's seed extraction + dynamic temporal memory.

Usage:
    from manipulation.temporal_memory import TemporalMemory
    mem = TemporalMemory()
    mem.add_seed("USDTRY_38", "USD/TRY 38'i asti", importance=0.9, tags=["macro","usdtry"])
    mem.add_seed("KAP_THYAO_temettu", "THYAO temettu acikladi", importance=0.7, tags=["kap","THYAO"])
    context = mem.query_context("THYAO", lookback_hours=24)
"""

import json
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime, timedelta

MEMORY_DIR = Path("data/temporal_memory")
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Seed:
    seed_id: str
    content: str
    timestamp: str
    importance: float  # 0-1
    tags: List[str] = field(default_factory=list)
    symbols: List[str] = field(default_factory=list)
    source: str = "manual"

    def to_dict(self) -> dict:
        return {
            "seed_id": self.seed_id,
            "content": self.content,
            "timestamp": self.timestamp,
            "importance": self.importance,
            "tags": self.tags,
            "symbols": self.symbols,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Seed":
        return cls(
            seed_id=d["seed_id"],
            content=d["content"],
            timestamp=d["timestamp"],
            importance=d.get("importance", 0.5),
            tags=d.get("tags", []),
            symbols=d.get("symbols", []),
            source=d.get("source", "manual"),
        )


class TemporalMemory:
    """
    Time-aware memory graph for macro/news/KAP seeds.
    Seeds decay in importance over time.
    """

    def __init__(self, decay_half_life_hours: float = 24.0, memory_dir: Path = MEMORY_DIR):
        self.decay_half_life = decay_half_life_hours
        self.memory_dir = memory_dir
        self._seeds: Dict[str, Seed] = {}
        self._load_all()

    def _seed_file(self) -> Path:
        return self.memory_dir / "seeds.jsonl"

    def _load_all(self):
        fpath = self._seed_file()
        if not fpath.exists():
            return
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    s = Seed.from_dict(d)
                    self._seeds[s.seed_id] = s
                except Exception:
                    continue

    def _save_seed(self, seed: Seed):
        fpath = self._seed_file()
        with open(fpath, "a", encoding="utf-8") as f:
            f.write(json.dumps(seed.to_dict(), ensure_ascii=False) + "\n")

    def add_seed(self, seed_id: str, content: str, importance: float = 0.5,
                 tags: Optional[List[str]] = None, symbols: Optional[List[str]] = None,
                 source: str = "manual"):
        """Add a temporal seed."""
        seed = Seed(
            seed_id=seed_id,
            content=content,
            timestamp=datetime.now().isoformat(),
            importance=importance,
            tags=tags or [],
            symbols=[s.upper() for s in (symbols or [])],
            source=source,
        )
        self._seeds[seed.seed_id] = seed
        self._save_seed(seed)

    def query_context(self, symbol: str, lookback_hours: float = 24.0,
                      min_importance: float = 0.3) -> List[dict]:
        """
        Retrieve relevant seeds for a symbol within lookback window.
        Returns sorted by decayed importance.
        """
        symbol = symbol.upper()
        now = datetime.now()
        cutoff = now - timedelta(hours=lookback_hours)
        results = []

        for seed in self._seeds.values():
            if symbol not in seed.symbols and not any(symbol in t.upper() for t in seed.tags):
                continue
            try:
                ts = datetime.fromisoformat(seed.timestamp)
            except Exception:
                continue
            if ts < cutoff:
                continue

            # Time decay
            hours_old = (now - ts).total_seconds() / 3600.0
            decayed = seed.importance * (0.5 ** (hours_old / self.decay_half_life))
            if decayed < min_importance:
                continue

            results.append({
                "seed_id": seed.seed_id,
                "content": seed.content,
                "decayed_importance": round(decayed, 3),
                "hours_old": round(hours_old, 1),
                "tags": seed.tags,
                "source": seed.source,
            })

        results.sort(key=lambda x: x["decayed_importance"], reverse=True)
        return results

    def get_macro_regime_from_seeds(self) -> dict:
        """Infer macro regime from recent macro seeds."""
        macro_seeds = [s for s in self._seeds.values() if "macro" in [t.lower() for t in s.tags]]
        if not macro_seeds:
            return {"regime": "NEUTRAL", "confidence": 0.0}

        # Simple sentiment: count bullish vs bearish keywords
        bullish = 0
        bearish = 0
        for s in macro_seeds:
            text = s.content.lower()
            if any(w in text for w in ["yukseldi", "artti", "pozitif", "bull", "buy", "guclu"]):
                bullish += s.importance
            if any(w in text for w in ["dustu", "azaldi", "negatif", "bear", "sell", "zayif"]):
                bearish += s.importance

        total = bullish + bearish
        if total == 0:
            return {"regime": "NEUTRAL", "confidence": 0.0}

        if bullish / total > 0.6:
            return {"regime": "BULL", "confidence": bullish / total}
        elif bearish / total > 0.6:
            return {"regime": "BEAR", "confidence": bearish / total}
        return {"regime": "NEUTRAL", "confidence": max(bullish, bearish) / total}

    def cleanup_old(self, max_age_hours: float = 168.0):
        """Remove seeds older than max_age_hours."""
        now = datetime.now()
        cutoff = now - timedelta(hours=max_age_hours)
        to_remove = []
        for sid, seed in self._seeds.items():
            try:
                ts = datetime.fromisoformat(seed.timestamp)
                if ts < cutoff:
                    to_remove.append(sid)
            except Exception:
                to_remove.append(sid)
        for sid in to_remove:
            del self._seeds[sid]
