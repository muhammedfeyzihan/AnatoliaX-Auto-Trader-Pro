"""
backtest/tick_simulator.py — Tick-Level Market Simulator (Phase 1)
Module 6 from anatoliax_prompt_v6.txt

Features:
  - Latency: L ~ LogNormal(mu, sigma)
  - Spread widening: S_stress = S_normal * (1 + beta * |dP|/sigma_P)
  - Slippage: slip = alpha1*(size/Q) + alpha2*sigma + alpha3*S
  - Queue depth decay: Q(t) = Q0 * exp(-lambda*t) + noise
  - Liquidity collapse trigger
  - Validation: |simulated_fill - live_fill| < epsilon for 95% of trades
"""

import math
import random
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Tuple
import hashlib


@dataclass
class TickSimulatorConfig:
    """Configuration for tick-level simulation."""
    mu_latency: float = 0.0          # Mean of log-normal latency (log scale)
    sigma_latency: float = 0.5       # Std dev of log-normal latency (log scale)
    beta_stress: float = 2.0         # Spread widening factor
    alpha1: float = 0.5              # Slippage coefficient for size/queue
    alpha2: float = 0.3              # Slippage coefficient for volatility
    alpha3: float = 0.2              # Slippage coefficient for spread
    lambda_decay: float = 0.1        # Queue depth decay rate
    noise_std: float = 0.05          # Queue noise standard deviation
    collapse_depth_threshold: float = 0.3      # Liquidity collapse threshold
    collapse_imbalance_threshold: float = -0.7 # Imbalance threshold for collapse
    seed: int = 42                   # Random seed for reproducibility


@dataclass
class SimulatedFill:
    """Result of a simulated fill."""
    fill_price: float
    latency_ms: float
    slippage: float
    spread_at_fill: float
    queue_depth_at_fill: float
    timestamp: datetime
    fill_id: str = ""

    def __post_init__(self):
        if not self.fill_id:
            self.fill_id = hashlib.sha256(
                f"{self.fill_price}{self.latency_ms}{self.timestamp}".encode()
            ).hexdigest()[:16]


class TickLevelMarketSimulator:
    """
    Realistic tick-level simulator with latency, slippage, spread widening, queue decay.
    
    Mathematical models:
      - Latency: L ~ LogNormal(mu_latency, sigma_latency)
      - Spread stress: S_stress = S_normal * (1 + beta * |dP|/sigma_P)
      - Slippage: slip = alpha1*(size/Q) + alpha2*sigma + alpha3*S
      - Queue decay: Q(t) = Q0 * exp(-lambda*t) + noise
      
    Validation requirement:
      |simulated_fill - live_fill| < 0.1 * spread for 95% of trades
    """

    def __init__(self, config: TickSimulatorConfig = None):
        self.config = config or TickSimulatorConfig()
        self._rng = random.Random(self.config.seed)
        self._validation_samples: List[Dict] = []
        self._fill_history: List[SimulatedFill] = []
        self._latency_samples: List[float] = []

    def sample_latency(self) -> float:
        """
        Sample latency from log-normal distribution.
        L ~ LogNormal(mu, sigma)
        
        Returns:
            Latency in seconds
        """
        lat = self._rng.lognormvariate(self.config.mu_latency, self.config.sigma_latency)
        self._latency_samples.append(lat)
        return lat

    def spread_stress(self, normal_spread: float, price_change: float, price_volatility: float) -> float:
        """
        Calculate stressed spread during market moves.
        S_stress = S_normal * (1 + beta * |dP|/sigma_P)
        
        Args:
            normal_spread: Normal bid-ask spread
            price_change: Absolute price change
            price_volatility: Price volatility (standard deviation)
        
        Returns:
            Stressed spread value
        """
        if price_volatility == 0 or normal_spread == 0:
            return normal_spread
        stress_factor = 1 + self.config.beta_stress * abs(price_change) / price_volatility
        return normal_spread * stress_factor

    def slippage(self, order_size: float, queue_depth: float, volatility: float, spread: float) -> float:
        """
        Calculate expected slippage.
        slip = alpha1*(size/Q) + alpha2*sigma + alpha3*S
        
        Args:
            order_size: Order size in shares
            queue_depth: Queue depth at best price
            volatility: Current volatility
            spread: Current bid-ask spread
        
        Returns:
            Expected slippage in price units
        """
        c = self.config
        size_impact = c.alpha1 * (order_size / (queue_depth + 1e-9))
        vol_impact = c.alpha2 * volatility
        spread_impact = c.alpha3 * spread
        return size_impact + vol_impact + spread_impact

    def queue_depth_decay(self, q0: float, t: float) -> float:
        """
        Model queue depth decay over time.
        Q(t) = Q0 * exp(-lambda*t) + noise
        
        Args:
            q0: Initial queue depth
            t: Time elapsed in seconds
        
        Returns:
            Queue depth at time t
        """
        decay = q0 * math.exp(-self.config.lambda_decay * t)
        noise = self._rng.gauss(0, self.config.noise_std * q0)
        return max(0.0, decay + noise)

    def liquidity_collapse_trigger(self, depth: float, dQ_dt: float, imbalance: float) -> bool:
        """
        Detect liquidity collapse conditions.
        
        Trigger when:
          - dQ/dt < -threshold (rapid depth decrease)
          - IMB < -0.7 (severe sell-side imbalance)
        
        Args:
            depth: Current order book depth
            dQ_dt: Rate of change of depth
            imbalance: Order book imbalance (-1 to 1)
        
        Returns:
            True if liquidity collapse detected
        """
        return (dQ_dt < -self.config.collapse_depth_threshold and 
                imbalance < self.config.collapse_imbalance_threshold)

    def simulate_fill(
        self,
        arrival_price: float,
        order_size: float,
        queue_depth: float,
        volatility: float,
        spread: float,
        side: str = "buy",
        timestamp: Optional[datetime] = None,
    ) -> SimulatedFill:
        """
        Simulate a realistic fill with latency and slippage.
        
        Args:
            arrival_price: Price when order arrived
            order_size: Order size in shares
            queue_depth: Queue depth at best price
            volatility: Current volatility
            spread: Current bid-ask spread
            side: "buy" or "sell"
            timestamp: Fill timestamp (default: now)
        
        Returns:
            SimulatedFill object with fill details
        """
        # Sample latency
        latency = self.sample_latency()
        
        # Calculate slippage
        slip = self.slippage(order_size, queue_depth, volatility, spread)
        
        # Determine fill price direction based on side and random component
        if side == "buy":
            # Buyers pay slippage (higher price)
            fill_price = arrival_price + slip
        else:
            # Sellers receive less (lower price)
            fill_price = arrival_price - slip
        
        ts = timestamp or datetime.now(timezone.utc)
        
        fill = SimulatedFill(
            fill_price=fill_price,
            latency_ms=latency * 1000,
            slippage=slip,
            spread_at_fill=spread,
            queue_depth_at_fill=queue_depth,
            timestamp=ts,
        )
        
        self._fill_history.append(fill)
        return fill

    def validate(self, simulated_fill: float, live_fill: float, spread: float, epsilon_ratio: float = 0.1) -> bool:
        """
        Validate simulated fill against live fill.
        |simulated_fill - live_fill| < epsilon_ratio * spread
        
        Args:
            simulated_fill: Simulated fill price
            live_fill: Actual live fill price
            spread: Spread at time of fill
            epsilon_ratio: Tolerance ratio (default 0.1 = 10% of spread)
        
        Returns:
            True if validation passed
        """
        return abs(simulated_fill - live_fill) < epsilon_ratio * spread

    def record_validation(self, simulated: float, live: float, spread: float):
        """Record a validation sample."""
        self._validation_samples.append({
            "simulated": simulated,
            "live": live,
            "spread": spread,
            "error": abs(simulated - live),
            "error_pct_of_spread": abs(simulated - live) / (spread + 1e-9),
            "valid": self.validate(simulated, live, spread),
        })

    def get_validation_stats(self) -> Dict[str, Any]:
        """
        Get validation statistics.
        
        Returns:
            Dict with validation metrics
        """
        from typing import Any
        
        if not self._validation_samples:
            return {
                "total_samples": 0,
                "valid_count": 0,
                "valid_pct": 0.0,
                "mean_error": 0.0,
                "validation_passed": False,
            }
        
        valid_count = sum(1 for s in self._validation_samples if s["valid"])
        total = len(self._validation_samples)
        errors = [s["error"] for s in self._validation_samples]
        error_pcts = [s["error_pct_of_spread"] for s in self._validation_samples]
        
        mean_error = statistics.mean(errors) if errors else 0.0
        std_error = statistics.stdev(errors) if len(errors) > 1 else 0.0
        valid_pct = valid_count / total * 100 if total > 0 else 0.0
        
        # Validation passes if 95% of fills are within 10% of spread
        validation_passed = valid_pct >= 95.0
        
        return {
            "total_samples": total,
            "valid_count": valid_count,
            "invalid_count": total - valid_count,
            "valid_pct": valid_pct,
            "mean_error": mean_error,
            "std_error": std_error,
            "max_error": max(errors) if errors else 0.0,
            "mean_error_pct_of_spread": statistics.mean(error_pcts) if error_pcts else 0.0,
            "validation_passed": validation_passed,
        }

    def get_latency_stats(self) -> Dict[str, float]:
        """
        Get latency distribution statistics.
        
        Returns:
            Dict with latency metrics
        """
        if not self._latency_samples:
            return {}
        
        lats_ms = [l * 1000 for l in self._latency_samples]
        return {
            "mean_ms": statistics.mean(lats_ms),
            "std_ms": statistics.stdev(lats_ms) if len(lats_ms) > 1 else 0.0,
            "min_ms": min(lats_ms),
            "max_ms": max(lats_ms),
            "median_ms": statistics.median(lats_ms),
            "p95_ms": sorted(lats_ms)[int(len(lats_ms) * 0.95)] if len(lats_ms) >= 20 else max(lats_ms),
            "p99_ms": sorted(lats_ms)[int(len(lats_ms) * 0.99)] if len(lats_ms) >= 100 else max(lats_ms),
        }

    def reset(self):
        """Reset all statistics and history."""
        self._rng = random.Random(self.config.seed)
        self._validation_samples = []
        self._fill_history = []
        self._latency_samples = []

    def batch_simulate_fills(
        self,
        orders: List[Dict[str, Any]],
        market_data: Dict[str, float],
    ) -> List[SimulatedFill]:
        """
        Simulate fills for a batch of orders.
        
        Args:
            orders: List of order dicts with keys: size, side, arrival_price
            market_data: Dict with keys: queue_depth, volatility, spread
        
        Returns:
            List of SimulatedFill objects
        """
        fills = []
        for order in orders:
            fill = self.simulate_fill(
                arrival_price=order["arrival_price"],
                order_size=order["size"],
                queue_depth=market_data["queue_depth"],
                volatility=market_data["volatility"],
                spread=market_data["spread"],
                side=order.get("side", "buy"),
            )
            fills.append(fill)
        return fills
