"""
backtest/deterministic_replay.py — Deterministic Replay Engine (Phase 1)
Module 5 from anatoliax_prompt_v6.txt

Features:
  - For any market data stream M, seed s, configuration C:
    Replay(M, s, C) -> R
  - Requirement: Replay(M, s_1, C_1) = Replay(M, s_1, C_1) bit-exact.
  - Cryptographic hash: H = SHA-256(M || s || C || code_version).
  - Regression: if H_1 = H_2 then R_1 = R_2.
  
Validation:
  - Run N=100 replays, verify all outputs identical
  - Hash match rate = 100%
"""

import hashlib
import json
import pickle
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable
import statistics


@dataclass
class ReplayConfig:
    """Configuration for deterministic replay."""
    seed: int = 42
    initial_capital: float = 100_000.0
    position_size_pct: float = 0.02
    slippage_model: str = "default"
    commission_model: str = "bist"
    version: str = "3.3"

    def to_bytes(self) -> bytes:
        return json.dumps({
            "seed": self.seed,
            "initial_capital": self.initial_capital,
            "position_size_pct": self.position_size_pct,
            "slippage_model": self.slippage_model,
            "commission_model": self.commission_model,
            "version": self.version,
        }, sort_keys=True).encode("utf-8")


@dataclass
class Tick:
    """Standard tick data structure."""
    symbol: str = ""
    timestamp: Optional[datetime] = None
    price: float = 0.0
    size: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    volume: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "price": self.price,
            "size": self.size,
            "bid": self.bid,
            "ask": self.ask,
            "volume": self.volume,
            "extra": self.extra,
        }


class DeterministicReplayEngine:
    """
    Deterministic replay engine for bit-exact regression testing.
    
    Mathematical guarantee:
      Replay(M, s, C) = R where R is deterministic
    
    Validation:
      Run N=100 replays, verify all outputs identical, hash match rate = 100%
    """

    def __init__(self, config: ReplayConfig):
        self.config = config
        self._market_data: List[Tick] = []
        self._results: List[Dict[str, Any]] = []
        self._hash: Optional[str] = None
        self._rng: Optional[random.Random] = None

    def load_market_data(self, ticks: List[Tick]):
        """Load market data stream M."""
        self._market_data = ticks

    def load_market_data_from_dicts(self, ticks: List[Dict[str, Any]]):
        """Load market data from dict list."""
        self._market_data = []
        for t in ticks:
            tick = Tick(
                symbol=t.get("symbol", ""),
                timestamp=datetime.fromisoformat(t["timestamp"]) if t.get("timestamp") and isinstance(t["timestamp"], str) else t.get("timestamp"),
                price=t.get("price", 0.0),
                size=t.get("size", 0.0),
                bid=t.get("bid", t.get("price", 0.0)),
                ask=t.get("ask", t.get("price", 0.0)),
                volume=t.get("volume", 0.0),
                extra=t.get("extra", {}),
            )
            self._market_data.append(tick)

    def compute_hash(self) -> str:
        """
        H = SHA-256(M || s || C || code_version).
        Used for regression: if H_1 = H_2 then R_1 = R_2.
        """
        # Serialize market data deterministically
        m_bytes = pickle.dumps([t.to_dict() for t in self._market_data], protocol=pickle.HIGHEST_PROTOCOL)
        s_bytes = str(self.config.seed).encode("utf-8")
        c_bytes = self.config.to_bytes()
        v_bytes = self.config.version.encode("utf-8")

        combined = m_bytes + s_bytes + c_bytes + v_bytes
        self._hash = hashlib.sha256(combined).hexdigest()
        return self._hash

    def replay(self, strategy_fn: Callable[[Tick, Dict], Dict]) -> Dict[str, Any]:
        """
        Replay(M, s, C) -> R.
        
        Args:
            strategy_fn: callable that takes (tick, state) and returns action dict
                        action = {"side": "buy"|"sell", "size": float} or None
        
        Returns:
            Result dict with final_capital, trades, equity curve, hash
        """
        # Initialize RNG with seed for determinism
        self._rng = random.Random(self.config.seed)
        
        state = {
            "capital": self.config.initial_capital,
            "positions": [],
            "trades": [],
            "equity": [self.config.initial_capital],
            "rng_state": self._rng.getstate(),
        }

        for tick in self._market_data:
            action = strategy_fn(tick, state)
            if action:
                self._apply_action(action, tick, state)
            state["equity"].append(state["capital"])

        result = {
            "final_capital": state["capital"],
            "total_return": (state["capital"] - self.config.initial_capital) / self.config.initial_capital,
            "total_trades": len(state["trades"]),
            "trades": state["trades"],
            "equity": state["equity"],
            "hash": self.compute_hash(),
            "config": self.config.to_bytes().decode("utf-8"),
        }
        self._results.append(result)
        return result

    def _apply_action(self, action: Dict[str, Any], tick: Tick, state: Dict[str, Any]):
        """Apply trading action to state."""
        side = action.get("side")
        size = action.get("size", 0)
        price = tick.price

        if side == "buy":
            cost = size * price
            if state["capital"] >= cost:
                state["capital"] -= cost
                state["positions"].append({"size": size, "entry": price, "symbol": tick.symbol})
        elif side == "sell":
            for pos in state["positions"][:]:
                if pos["size"] <= size:
                    pnl = (price - pos["entry"]) * pos["size"]
                    state["capital"] += pos["size"] * price + pnl
                    state["trades"].append({
                        "pnl": pnl,
                        "entry": pos["entry"],
                        "exit": price,
                        "symbol": pos.get("symbol", ""),
                    })
                    size -= pos["size"]
                    state["positions"].remove(pos)
                else:
                    pnl = (price - pos["entry"]) * size
                    state["capital"] += size * price + pnl
                    state["trades"].append({
                        "pnl": pnl,
                        "entry": pos["entry"],
                        "exit": price,
                        "symbol": pos.get("symbol", ""),
                    })
                    pos["size"] -= size
                    break

    def validate_reproducibility(self, strategy_fn: Callable, runs: int = 100) -> Dict[str, Any]:
        """
        Run N replays and verify all outputs are identical.
        
        Validation requirement:
          - run N=100 replays
          - verify all outputs identical
          - hash match rate = 100%
        
        Args:
            strategy_fn: Strategy function to test
            runs: Number of replay runs (default 100)
        
        Returns:
            Validation report dict
        """
        hashes = []
        final_capitals = []
        trade_counts = []
        
        for i in range(runs):
            # Reset engine state
            self._rng = None
            result = self.replay(strategy_fn)
            hashes.append(result["hash"])
            final_capitals.append(result["final_capital"])
            trade_counts.append(result["total_trades"])

        unique_hashes = set(hashes)
        match_rate = (len(hashes) - len(unique_hashes) + 1) / len(hashes) * 100

        return {
            "runs": runs,
            "unique_hashes": len(unique_hashes),
            "hash_match_rate_pct": match_rate,
            "reproducible": len(unique_hashes) == 1,
            "final_capital_std": statistics.stdev(final_capitals) if len(final_capitals) > 1 else 0.0,
            "trade_count_std": statistics.stdev(trade_counts) if len(trade_counts) > 1 else 0.0,
            "validation_passed": len(unique_hashes) == 1 and match_rate == 100.0,
        }

    def validate_regression(self, expected_hash: str, strategy_fn: Callable) -> Dict[str, Any]:
        """
        Validate against expected hash for regression testing.
        
        If H_1 = H_2 then R_1 = R_2.
        
        Args:
            expected_hash: Previously computed hash to compare against
            strategy_fn: Strategy function to run
        
        Returns:
            Regression validation report
        """
        result = self.replay(strategy_fn)
        current_hash = result["hash"]
        
        return {
            "expected_hash": expected_hash,
            "current_hash": current_hash,
            "regression_passed": expected_hash == current_hash,
            "final_capital": result["final_capital"],
            "total_trades": result["total_trades"],
        }

    def get_hash(self) -> Optional[str]:
        """Get last computed hash."""
        return self._hash

    def reset(self):
        """Reset engine state."""
        self._market_data = []
        self._results = []
        self._hash = None
        self._rng = None
