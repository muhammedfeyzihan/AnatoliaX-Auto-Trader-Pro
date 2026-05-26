"""
memory.py — Agent memory persistence, reinforcement learning loop
"""
import json
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pathlib import Path


class AgentMemory:
    """
    Her ajanin karar gecmisi, basari orani ve ogrenme katsayisi.
    Q-learning benzeri basit reinforcement loop.
    """

    def __init__(self, agent: str, memory_dir: str = "data/agent_memory"):
        self.agent = agent
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.file = self.memory_dir / f"{agent}.json"
        self._data = self._load()

    def _load(self) -> dict:
        if self.file.exists():
            return json.loads(self.file.read_text(encoding="utf-8"))
        return {
            "agent": self.agent,
            "decisions": [],
            "q_table": {},
            "alpha": 0.1,
            "gamma": 0.9,
            "epsilon": 0.2,
        }

    def save(self):
        self.file.write_text(json.dumps(self._data, ensure_ascii=False, indent=2, default=str))

    def record_decision(self, state: str, action: str, reward: float):
        """Bir karari ve odulunu kaydet."""
        self._data["decisions"].append({
            "state": state,
            "action": action,
            "reward": reward,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # Q-table guncelle (basit Q-learning)
        q = self._data["q_table"]
        key = f"{state}:{action}"
        old = q.get(key, 0.0)
        alpha = self._data["alpha"]
        gamma = self._data["gamma"]
        # Basit update: Q = (1-alpha)*Q + alpha*reward
        q[key] = (1 - alpha) * old + alpha * reward
        self.save()

    def best_action(self, state: str, actions: List[str]) -> str:
        """Mevcut state icin en iyi aksiyonu sec (epsilon-greedy)."""
        if np.random.random() < self._data["epsilon"]:
            return np.random.choice(actions)
        q = self._data["q_table"]
        best = None
        best_val = -float("inf")
        for a in actions:
            val = q.get(f"{state}:{a}", 0.0)
            if val > best_val:
                best_val = val
                best = a
        return best if best else actions[0]

    def get_stats(self) -> dict:
        decisions = self._data["decisions"]
        if not decisions:
            return {"total": 0, "avg_reward": 0.0}
        rewards = [d["reward"] for d in decisions]
        return {
            "total": len(decisions),
            "avg_reward": round(np.mean(rewards), 4),
            "last_10_avg": round(np.mean(rewards[-10:]), 4) if len(rewards) >= 10 else round(np.mean(rewards), 4),
        }
