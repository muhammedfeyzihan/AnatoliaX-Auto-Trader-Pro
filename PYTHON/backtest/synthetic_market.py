"""
backtest/synthetic_market.py - Synthetic Market Generator

Generates adversarial market environments, flash crashes, manipulated orderbooks.
"""

import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
import random


@dataclass
class MarketScenario:
    scenario_id: str
    scenario_type: str
    duration_sec: float
    volatility_multiplier: float
    liquidity_factor: float
    manipulation_present: bool
    timestamp: str


@dataclass
class SyntheticTick:
    timestamp: str
    price: float
    volume: float
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    is_manipulated: bool


class SyntheticMarketGenerator:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        self._scenarios: List[MarketScenario] = []
        self._generated_ticks: List[SyntheticTick] = []
    
    def generate_normal_market(self, base_price: float = 100.0,
                               num_ticks: int = 10000) -> List[SyntheticTick]:
        ticks = []
        price = base_price
        
        for i in range(num_ticks):
            volatility = 0.0001
            price_change = self.rng.normal(0, volatility * price)
            price = max(price + price_change, 1.0)
            
            spread = price * 0.001
            bid = price - spread / 2
            ask = price + spread / 2
            
            tick = SyntheticTick(
                timestamp=datetime.now(timezone.utc).isoformat(),
                price=price,
                volume=self.rng.uniform(100, 1000),
                bid=bid,
                ask=ask,
                bid_size=self.rng.uniform(1000, 5000),
                ask_size=self.rng.uniform(1000, 5000),
                is_manipulated=False,
            )
            ticks.append(tick)
        
        self._generated_ticks.extend(ticks)
        return ticks
    
    def generate_flash_crash(self, base_price: float = 100.0,
                            crash_depth: float = 0.10,
                            recovery_time: int = 100) -> List[SyntheticTick]:
        ticks = []
        price = base_price
        
        for i in range(recovery_time * 2):
            if i < recovery_time:
                crash_factor = crash_depth * (i / recovery_time)
                price = base_price * (1 - crash_factor)
                volatility = 0.01
            else:
                recovery_factor = crash_depth * ((i - recovery_time) / recovery_time)
                price = base_price * (1 - crash_depth + recovery_factor)
                volatility = 0.005
            
            price_change = self.rng.normal(0, volatility * price)
            price = max(price + price_change, 1.0)
            
            spread = price * 0.005
            tick = SyntheticTick(
                timestamp=datetime.now(timezone.utc).isoformat(),
                price=price,
                volume=self.rng.uniform(5000, 50000),
                bid=price - spread / 2,
                ask=price + spread / 2,
                bid_size=self.rng.uniform(100, 1000),
                ask_size=self.rng.uniform(100, 1000),
                is_manipulated=(i < recovery_time),
            )
            ticks.append(tick)
        
        scenario = MarketScenario(
            scenario_id=f"flash_crash_{len(self._scenarios)}",
            scenario_type="flash_crash",
            duration_sec=recovery_time * 2,
            volatility_multiplier=10.0,
            liquidity_factor=0.1,
            manipulation_present=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._scenarios.append(scenario)
        self._generated_ticks.extend(ticks)
        return ticks
    
    def generate_manipulated_orderbook(self, base_price: float = 100.0,
                                       num_ticks: int = 1000) -> List[SyntheticTick]:
        ticks = []
        price = base_price
        
        for i in range(num_ticks):
            is_manipulation = (i % 10 < 3)
            
            if is_manipulation:
                fake_spread = price * 0.02
                bid = price - fake_spread
                ask = price + fake_spread * 0.1
                bid_size = self.rng.uniform(50000, 100000)
                ask_size = self.rng.uniform(100, 500)
            else:
                spread = price * 0.001
                bid = price - spread / 2
                ask = price + spread / 2
                bid_size = self.rng.uniform(1000, 5000)
                ask_size = self.rng.uniform(1000, 5000)
            
            tick = SyntheticTick(
                timestamp=datetime.now(timezone.utc).isoformat(),
                price=price,
                volume=self.rng.uniform(100, 1000),
                bid=bid,
                ask=ask,
                bid_size=bid_size,
                ask_size=ask_size,
                is_manipulated=is_manipulation,
            )
            ticks.append(tick)
        
        scenario = MarketScenario(
            scenario_id=f"manipulation_{len(self._scenarios)}",
            scenario_type="spoofing",
            duration_sec=num_ticks,
            volatility_multiplier=1.0,
            liquidity_factor=1.0,
            manipulation_present=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._scenarios.append(scenario)
        self._generated_ticks.extend(ticks)
        return ticks
    
    def generate_liquidity_crisis(self, base_price: float = 100.0,
                                  num_ticks: int = 500) -> List[SyntheticTick]:
        ticks = []
        price = base_price
        
        for i in range(num_ticks):
            volatility = 0.005 + (i / num_ticks) * 0.02
            price_change = self.rng.normal(0, volatility * price)
            price = max(price + price_change, 1.0)
            
            spread = price * (0.001 + (i / num_ticks) * 0.05)
            liquidity_factor = 1.0 - (i / num_ticks) * 0.9
            
            tick = SyntheticTick(
                timestamp=datetime.now(timezone.utc).isoformat(),
                price=price,
                volume=self.rng.uniform(10, 100) * liquidity_factor,
                bid=price - spread / 2,
                ask=price + spread / 2,
                bid_size=self.rng.uniform(100, 500) * liquidity_factor,
                ask_size=self.rng.uniform(100, 500) * liquidity_factor,
                is_manipulated=False,
            )
            ticks.append(tick)
        
        scenario = MarketScenario(
            scenario_id=f"liquidity_crisis_{len(self._scenarios)}",
            scenario_type="liquidity_crisis",
            duration_sec=num_ticks,
            volatility_multiplier=5.0,
            liquidity_factor=0.1,
            manipulation_present=False,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._scenarios.append(scenario)
        self._generated_ticks.extend(ticks)
        return ticks
    
    def get_scenario_report(self) -> Dict[str, Any]:
        return {
            'total_scenarios': len(self._scenarios),
            'total_ticks': len(self._generated_ticks),
            'scenarios': [
                {
                    'id': s.scenario_id,
                    'type': s.scenario_type,
                    'manipulation': s.manipulation_present,
                }
                for s in self._scenarios
            ],
        }


_synthetic_gen: Optional[SyntheticMarketGenerator] = None

def get_synthetic_market_generator(seed: int = 42) -> SyntheticMarketGenerator:
    global _synthetic_gen
    if _synthetic_gen is None:
        _synthetic_gen = SyntheticMarketGenerator(seed=seed)
    return _synthetic_gen
