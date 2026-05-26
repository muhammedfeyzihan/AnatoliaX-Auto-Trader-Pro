"""
agents/meta_learning.py - AI Meta-Learning Layer

Reinforcement-based strategy mutation, autonomous alpha discovery,
strategy retirement logic, adaptive reward shaping, online learning.
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import random


@dataclass
class StrategyMutation:
    mutation_id: str
    parent_strategy: str
    mutation_type: str
    parameters_changed: Dict[str, float]
    performance_delta: float
    timestamp: str
    accepted: bool = False


@dataclass
class AlphaSignal:
    signal_id: str
    feature_combination: List[str]
    predictive_power: float
    decay_rate: float
    discovery_date: str
    active: bool = True


@dataclass
class StrategyLifecycle:
    strategy_id: str
    created_date: str
    paper_trades: int
    live_trades: int
    total_pnl: float
    sharpe_ratio: float
    max_drawdown: float
    status: str  # research, paper, live, retired
    retirement_reason: Optional[str] = None


class MetaLearningEngine:
    def __init__(self, mutation_rate: float = 0.1):
        self.mutation_rate = mutation_rate
        self._mutations: List[StrategyMutation] = []
        self._alpha_signals: List[AlphaSignal] = []
        self._strategy_lifecycles: Dict[str, StrategyLifecycle] = {}
        self._reward_history: Dict[str, List[float]] = {}
        self._feature_importance: Dict[str, float] = {}
    
    def mutate_strategy(self, strategy_id: str, 
                       current_params: Dict[str, float],
                       performance: float) -> StrategyMutation:
        mutation_id = hashlib.sha256(
            f"{strategy_id}{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:16]
        
        mutated_params = current_params.copy()
        changed_params = {}
        
        for param in current_params:
            if random.random() < self.mutation_rate:
                delta = np.random.normal(0, 0.1)
                mutated_params[param] = current_params[param] * (1 + delta)
                changed_params[param] = delta
        
        mutation = StrategyMutation(
            mutation_id=mutation_id,
            parent_strategy=strategy_id,
            mutation_type="gaussian_perturbation",
            parameters_changed=changed_params,
            performance_delta=0.0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            accepted=False,
        )
        
        self._mutations.append(mutation)
        return mutation
    
    def evaluate_mutation(self, mutation_id: str, 
                         new_performance: float,
                         baseline_performance: float) -> bool:
        performance_delta = (new_performance - baseline_performance) / (abs(baseline_performance) + 1e-6)
        
        for mutation in self._mutations:
            if mutation.mutation_id == mutation_id:
                mutation.performance_delta = performance_delta
                mutation.accepted = (performance_delta > 0.05)
                return mutation.accepted
        
        return False
    
    def discover_alpha(self, features: Dict[str, float],
                      target: float,
                      min_predictive_power: float = 0.6) -> Optional[AlphaSignal]:
        signal_id = hashlib.sha256(
            f"alpha_{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:16]
        
        feature_combo = list(features.keys())
        predictive_power = abs(np.corrcoef(list(features.values()), [target])[0, 1])
        
        if predictive_power >= min_predictive_power:
            signal = AlphaSignal(
                signal_id=signal_id,
                feature_combination=feature_combo,
                predictive_power=predictive_power,
                decay_rate=0.1,
                discovery_date=datetime.now(timezone.utc).isoformat(),
                active=True,
            )
            self._alpha_signals.append(signal)
            return signal
        
        return None
    
    def retire_strategy(self, strategy_id: str, 
                       reason: str) -> Optional[StrategyLifecycle]:
        if strategy_id not in self._strategy_lifecycles:
            return None
        
        lifecycle = self._strategy_lifecycles[strategy_id]
        lifecycle.status = "retired"
        lifecycle.retirement_reason = reason
        
        print(f"[META-LEARNING] Retired strategy {strategy_id}: {reason}")
        return lifecycle
    
    def check_strategy_death(self, strategy_id: str,
                            max_drawdown: float,
                            min_sharpe: float,
                            min_winrate: float) -> bool:
        if strategy_id not in self._strategy_lifecycles:
            return False
        
        lifecycle = self._strategy_lifecycles[strategy_id]
        
        should_retire = (
            lifecycle.max_drawdown > max_drawdown or
            lifecycle.sharpe_ratio < min_sharpe
        )
        
        if should_retire:
            reason = f"DD={lifecycle.max_drawdown:.2f}, Sharpe={lifecycle.sharpe_ratio:.2f}"
            self.retire_strategy(strategy_id, reason)
            return True
        
        return False
    
    def update_reward(self, strategy_id: str, reward: float) -> None:
        if strategy_id not in self._reward_history:
            self._reward_history[strategy_id] = []
        self._reward_history[strategy_id].append(reward)
    
    def get_adaptive_reward(self, strategy_id: str) -> float:
        if strategy_id not in self._reward_history or len(self._reward_history[strategy_id]) == 0:
            return 0.0
        
        rewards = self._reward_history[strategy_id][-100:]
        return float(np.mean(rewards))
    
    def register_strategy(self, strategy_id: str) -> StrategyLifecycle:
        lifecycle = StrategyLifecycle(
            strategy_id=strategy_id,
            created_date=datetime.now(timezone.utc).isoformat(),
            paper_trades=0,
            live_trades=0,
            total_pnl=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            status="research",
        )
        self._strategy_lifecycles[strategy_id] = lifecycle
        return lifecycle
    
    def update_strategy_lifecycle(self, strategy_id: str,
                                 paper_trades: Optional[int] = None,
                                 live_trades: Optional[int] = None,
                                 pnl: Optional[float] = None,
                                 sharpe: Optional[float] = None,
                                 drawdown: Optional[float] = None) -> None:
        if strategy_id not in self._strategy_lifecycles:
            self.register_strategy(strategy_id)
        
        lifecycle = self._strategy_lifecycles[strategy_id]
        
        if paper_trades is not None:
            lifecycle.paper_trades = paper_trades
        if live_trades is not None:
            lifecycle.live_trades = live_trades
        if pnl is not None:
            lifecycle.total_pnl = pnl
        if sharpe is not None:
            lifecycle.sharpe_ratio = sharpe
        if drawdown is not None:
            lifecycle.max_drawdown = drawdown
        
        if lifecycle.paper_trades >= 100 and lifecycle.status == "research":
            lifecycle.status = "paper"
        elif lifecycle.live_trades >= 50 and lifecycle.status == "paper":
            lifecycle.status = "live"
    
    def get_meta_learning_report(self) -> Dict[str, Any]:
        active_strategies = sum(1 for l in self._strategy_lifecycles.values() if l.status == "live")
        retired_strategies = sum(1 for l in self._strategy_lifecycles.values() if l.status == "retired")
        active_alphas = sum(1 for a in self._alpha_signals if a.active)
        
        return {
            'total_mutations': len(self._mutations),
            'accepted_mutations': sum(1 for m in self._mutations if m.accepted),
            'alpha_signals_discovered': len(self._alpha_signals),
            'active_alphas': active_alphas,
            'total_strategies': len(self._strategy_lifecycles),
            'active_strategies': active_strategies,
            'retired_strategies': retired_strategies,
            'strategies_by_status': {
                'research': sum(1 for l in self._strategy_lifecycles.values() if l.status == 'research'),
                'paper': sum(1 for l in self._strategy_lifecycles.values() if l.status == 'paper'),
                'live': active_strategies,
                'retired': retired_strategies,
            },
        }


_meta_learning: Optional[MetaLearningEngine] = None

def get_meta_learning_engine() -> MetaLearningEngine:
    global _meta_learning
    if _meta_learning is None:
        _meta_learning = MetaLearningEngine()
    return _meta_learning
