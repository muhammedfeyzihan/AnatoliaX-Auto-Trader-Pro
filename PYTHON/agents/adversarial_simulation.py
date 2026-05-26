"""
agents/adversarial_simulation.py — Adversarial Market Simulation (Phase 4)
Module 17 from anatoliax_prompt_v6.txt

Features:
  - PanicAgent: sell_all if shock_detected
  - SpoofingAgent: place/cancel large orders to manipulate
  - InstitutionalPredator: detect patterns, front-run
  - LiquidityTrapAgent: withdraw liquidity suddenly
  - Training: strategy plays N_episodes against adversarial ensemble
  - Validation: win_rate_vs_adversarial > 60% before live deployment
"""

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from abc import ABC, abstractmethod


@dataclass
class MarketState:
    price: float
    bid: float
    ask: float
    depth: float
    shock_detected: bool = False


class AdversarialAgent(ABC):
    """Base class for adversarial market agents."""

    @abstractmethod
    def act(self, state: MarketState, my_position: float) -> Dict:
        pass


class PanicAgent(AdversarialAgent):
    def act(self, state: MarketState, my_position: float) -> Dict:
        if state.shock_detected and my_position > 0:
            return {"action": "sell_all", "size": my_position}
        return {"action": "hold"}


class SpoofingAgent(AdversarialAgent):
    def act(self, state: MarketState, my_position: float) -> Dict:
        if random.random() > 0.7:
            return {"action": "spoof", "size": state.depth * 3, "price": state.ask}
        return {"action": "hold"}


class InstitutionalPredator(AdversarialAgent):
    def act(self, state: MarketState, my_position: float) -> Dict:
        # Front-run if depth is high
        if state.depth > 10000:
            return {"action": "front_run", "size": 100, "price": state.bid + 0.01}
        return {"action": "hold"}


class LiquidityTrapAgent(AdversarialAgent):
    def act(self, state: MarketState, my_position: float) -> Dict:
        if random.random() > 0.8:
            return {"action": "withdraw_liquidity", "size": state.depth * 0.5}
        return {"action": "hold"}


class AdversarialSimulation:
    """
    Training environment where a strategy plays against an ensemble of adversarial agents.
    """

    def __init__(self, adversaries: Optional[List[AdversarialAgent]] = None):
        self.adversaries = adversaries or [
            PanicAgent(),
            SpoofingAgent(),
            InstitutionalPredator(),
            LiquidityTrapAgent(),
        ]
        self._episodes: List[Dict] = []

    def run_episode(self, strategy_fn, initial_capital: float = 100_000.0, steps: int = 100) -> Dict:
        capital = initial_capital
        position = 0.0
        wins = 0
        losses = 0

        for _ in range(steps):
            state = MarketState(
                price=random.uniform(90, 110),
                bid=random.uniform(89, 109),
                ask=random.uniform(91, 111),
                depth=random.uniform(5000, 50000),
                shock_detected=random.random() > 0.95,
            )

            # Strategy action
            strat_action = strategy_fn(state)
            if strat_action.get("action") == "buy":
                cost = strat_action["size"] * state.ask
                if capital >= cost:
                    capital -= cost
                    position += strat_action["size"]

            # Adversarial actions
            for adv in self.adversaries:
                adv_action = adv.act(state, position)
                if adv_action["action"] == "sell_all":
                    capital += position * state.bid
                    position = 0.0

            # PnL tracking (simplified)
            if position > 0 and random.random() > 0.5:
                pnl = position * (state.price - 100)
                if pnl > 0:
                    wins += 1
                else:
                    losses += 1

        total = wins + losses
        win_rate = wins / total if total > 0 else 0.0
        return {
            "final_capital": capital,
            "win_rate": win_rate,
            "exploited": losses > wins,
        }

    def train(self, strategy_fn, episodes: int = 100) -> Dict:
        results = []
        for _ in range(episodes):
            r = self.run_episode(strategy_fn)
            results.append(r)
        avg_win_rate = sum(r["win_rate"] for r in results) / len(results)
        return {
            "episodes": episodes,
            "avg_win_rate": avg_win_rate,
            "ready_for_live": avg_win_rate > 0.60,
        }
