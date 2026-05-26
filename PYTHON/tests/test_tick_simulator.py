"""
test_tick_simulator.py — Comprehensive tests for TickLevelMarketSimulator

Validation requirements:
  - |simulated_fill - live_fill| < 0.1 * spread for 95% of trades
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backtest.tick_simulator import TickLevelMarketSimulator, TickSimulatorConfig, SimulatedFill


class TestTickSimulatorConfig:
    """Tests for TickSimulatorConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = TickSimulatorConfig()
        
        assert config.mu_latency == 0.0
        assert config.sigma_latency == 0.5
        assert config.beta_stress == 2.0
        assert config.alpha1 == 0.5
        assert config.alpha2 == 0.3
        assert config.alpha3 == 0.2
        assert config.lambda_decay == 0.1
        assert config.seed == 42

    def test_custom_values(self):
        """Test custom configuration."""
        config = TickSimulatorConfig(
            mu_latency=1.0,
            sigma_latency=0.3,
            beta_stress=3.0,
            seed=123
        )
        
        assert config.mu_latency == 1.0
        assert config.sigma_latency == 0.3
        assert config.beta_stress == 3.0
        assert config.seed == 123


class TestTickLevelMarketSimulator:
    """Tests for TickLevelMarketSimulator."""

    @pytest.fixture
    def simulator(self):
        """Create simulator with default config."""
        return TickLevelMarketSimulator(TickSimulatorConfig(seed=42))

    @pytest.fixture
    def market_data(self):
        """Sample market data."""
        return {
            "queue_depth": 10000,
            "volatility": 0.02,
            "spread": 0.5,
        }

    def test_sample_latency_positive(self, simulator):
        """Test that latency samples are always positive."""
        latencies = [simulator.sample_latency() for _ in range(100)]
        
        for lat in latencies:
            assert lat > 0

    def test_sample_latency_distribution(self):
        """Test latency distribution parameters."""
        config = TickSimulatorConfig(mu_latency=0.0, sigma_latency=0.5, seed=42)
        simulator = TickLevelMarketSimulator(config)
        
        latencies = [simulator.sample_latency() for _ in range(1000)]
        
        # Log-normal should have positive skew
        assert min(latencies) > 0
        assert max(latencies) < 10  # Reasonable upper bound

    def test_spread_stress_increase(self, simulator):
        """Test that spread increases during stress."""
        normal_spread = 0.5
        stressed_spread = simulator.spread_stress(
            normal_spread=normal_spread,
            price_change=0.05,
            price_volatility=0.01
        )
        
        assert stressed_spread > normal_spread

    def test_spread_stress_zero_volatility(self, simulator):
        """Test spread stress with zero volatility."""
        spread = simulator.spread_stress(
            normal_spread=0.5,
            price_change=0.05,
            price_volatility=0.0
        )
        
        assert spread == 0.5  # Should return normal spread

    def test_spread_stress_formula(self):
        """Test spread stress formula: S_stress = S_normal * (1 + beta * |dP|/sigma_P)."""
        config = TickSimulatorConfig(beta_stress=2.0, seed=42)
        simulator = TickLevelMarketSimulator(config)
        
        normal_spread = 0.5
        price_change = 0.02
        price_volatility = 0.01
        
        expected = normal_spread * (1 + 2.0 * abs(0.02) / 0.01)
        actual = simulator.spread_stress(normal_spread, price_change, price_volatility)
        
        assert abs(actual - expected) < 1e-6

    def test_slippage_positive(self, simulator):
        """Test that slippage is always positive."""
        slip = simulator.slippage(
            order_size=1000,
            queue_depth=5000,
            volatility=0.02,
            spread=0.5
        )
        
        assert slip > 0

    def test_slippage_formula(self):
        """Test slippage formula: slip = alpha1*(size/Q) + alpha2*sigma + alpha3*S."""
        config = TickSimulatorConfig(alpha1=0.5, alpha2=0.3, alpha3=0.2, seed=42)
        simulator = TickLevelMarketSimulator(config)
        
        size, queue, vol, spread = 1000, 5000, 0.02, 0.5
        
        expected = 0.5 * (1000/5000) + 0.3 * 0.02 + 0.2 * 0.5
        actual = simulator.slippage(size, queue, vol, spread)
        
        assert abs(actual - expected) < 1e-6

    def test_slippage_increases_with_size(self, simulator):
        """Test that slippage increases with order size."""
        slip1 = simulator.slippage(100, 5000, 0.02, 0.5)
        slip2 = simulator.slippage(1000, 5000, 0.02, 0.5)
        slip3 = simulator.slippage(10000, 5000, 0.02, 0.5)
        
        assert slip1 < slip2 < slip3

    def test_slippage_increases_with_volatility(self, simulator):
        """Test that slippage increases with volatility."""
        slip1 = simulator.slippage(1000, 5000, 0.01, 0.5)
        slip2 = simulator.slippage(1000, 5000, 0.02, 0.5)
        slip3 = simulator.slippage(1000, 5000, 0.05, 0.5)
        
        assert slip1 < slip2 < slip3

    def test_queue_depth_decay(self, simulator):
        """Test queue depth decay over time."""
        q0 = 10000
        q1 = simulator.queue_depth_decay(q0, 0)
        q2 = simulator.queue_depth_decay(q0, 10)
        q3 = simulator.queue_depth_decay(q0, 100)
        
        assert q1 <= q0
        assert q2 < q1
        assert q3 < q2

    def test_queue_depth_decay_formula(self):
        """Test queue decay formula: Q(t) = Q0 * exp(-lambda*t) + noise."""
        config = TickSimulatorConfig(lambda_decay=0.1, noise_std=0.0, seed=42)
        simulator = TickLevelMarketSimulator(config)
        
        import math
        q0, t = 10000, 10
        expected = q0 * math.exp(-0.1 * t)
        actual = simulator.queue_depth_decay(q0, t)
        
        # Allow small tolerance due to floating point
        assert abs(actual - expected) < 1e-6

    def test_queue_depth_non_negative(self, simulator):
        """Test that queue depth never goes negative."""
        for t in range(100):
            q = simulator.queue_depth_decay(1000, t)
            assert q >= 0

    def test_liquidity_collapse_trigger(self, simulator):
        """Test liquidity collapse detection."""
        # Normal conditions - no collapse
        assert simulator.liquidity_collapse_trigger(
            depth=0.8, dQ_dt=-0.1, imbalance=-0.3
        ) is False
        
        # Collapse conditions
        assert simulator.liquidity_collapse_trigger(
            depth=0.2, dQ_dt=-0.5, imbalance=-0.8
        ) is True

    def test_simulate_fill_buy(self, simulator, market_data):
        """Test simulating a buy fill."""
        fill = simulator.simulate_fill(
            arrival_price=100.0,
            order_size=1000,
            queue_depth=market_data["queue_depth"],
            volatility=market_data["volatility"],
            spread=market_data["spread"],
            side="buy",
        )
        
        assert fill.fill_price > 100.0  # Buyers pay slippage
        assert fill.latency_ms > 0
        assert fill.slippage > 0
        assert fill.fill_id is not None

    def test_simulate_fill_sell(self, simulator, market_data):
        """Test simulating a sell fill."""
        fill = simulator.simulate_fill(
            arrival_price=100.0,
            order_size=1000,
            queue_depth=market_data["queue_depth"],
            volatility=market_data["volatility"],
            spread=market_data["spread"],
            side="sell",
        )
        
        assert fill.fill_price < 100.0  # Sellers receive less
        assert fill.latency_ms > 0
        assert fill.slippage > 0

    def test_simulate_fill_records_history(self, simulator, market_data):
        """Test that fills are recorded in history."""
        initial_count = len(simulator._fill_history)
        
        simulator.simulate_fill(
            arrival_price=100.0,
            order_size=1000,
            queue_depth=market_data["queue_depth"],
            volatility=market_data["volatility"],
            spread=market_data["spread"],
        )
        
        assert len(simulator._fill_history) == initial_count + 1

    def test_validate(self, simulator):
        """Test fill validation."""
        # Valid fill (within 10% of spread)
        assert simulator.validate(100.0, 100.05, 0.5, epsilon_ratio=0.1) is True
        
        # Invalid fill (outside 10% of spread)
        assert simulator.validate(100.0, 110.0, 0.5, epsilon_ratio=0.1) is False

    def test_validate_stricter_tolerance(self):
        """Test validation with stricter tolerance."""
        simulator = TickLevelMarketSimulator(TickSimulatorConfig(seed=42))
        
        # Passes at 10% tolerance
        assert simulator.validate(100.0, 100.05, 0.5, epsilon_ratio=0.1) is True
        
        # Fails at 5% tolerance (0.05 > 0.05 * 0.5 = 0.025)
        assert simulator.validate(100.0, 100.05, 0.5, epsilon_ratio=0.05) is False

    def test_record_validation(self, simulator):
        """Test recording validation samples."""
        simulator.record_validation(100.0, 100.05, 0.5)
        simulator.record_validation(100.0, 100.1, 0.5)
        
        assert len(simulator._validation_samples) == 2
        assert simulator._validation_samples[0]["valid"] is True

    def test_get_validation_stats_empty(self, simulator):
        """Test validation stats with no samples."""
        stats = simulator.get_validation_stats()
        
        assert stats["total_samples"] == 0
        assert stats["valid_pct"] == 0.0
        assert stats["validation_passed"] is False

    def test_get_validation_stats_with_samples(self, simulator):
        """Test validation stats with samples."""
        # Record samples with small errors (within tolerance)
        for i in range(95):
            # Error = i * 0.0005, max error = 0.047 (within 0.05 = 10% of 0.5 spread)
            simulator.record_validation(100.0, 100.0 + i * 0.0005, 0.5)
        # Record 5 samples with large errors (outside tolerance)
        for i in range(5):
            # Error = 0.06 + i * 0.01 (outside 0.05 tolerance)
            simulator.record_validation(100.0, 100.0 + 0.06 + i * 0.01, 0.5)
        
        stats = simulator.get_validation_stats()
        
        assert stats["total_samples"] == 100
        assert stats["valid_count"] == 95
        assert stats["valid_pct"] == 95.0
        assert stats["validation_passed"] is True  # 95% >= 95% threshold

    def test_get_validation_stats_fails_below_threshold(self, simulator):
        """Test validation fails when below 95% threshold."""
        # Record 90 valid samples
        for i in range(90):
            simulator.record_validation(100.0, 100.0 + i * 0.0005, 0.5)
        # Record 10 invalid samples
        for i in range(10):
            simulator.record_validation(100.0, 100.0 + 0.06 + i * 0.01, 0.5)
        
        stats = simulator.get_validation_stats()
        
        assert stats["total_samples"] == 100
        assert stats["valid_pct"] == 90.0
        assert stats["validation_passed"] is False

    def test_get_latency_stats(self, simulator):
        """Test latency statistics."""
        for _ in range(100):
            simulator.sample_latency()
        
        stats = simulator.get_latency_stats()
        
        assert "mean_ms" in stats
        assert "std_ms" in stats
        assert "min_ms" in stats
        assert "max_ms" in stats
        assert "median_ms" in stats
        assert "p95_ms" in stats
        assert "p99_ms" in stats
        assert stats["mean_ms"] > 0

    def test_get_latency_stats_empty(self, simulator):
        """Test latency stats with no samples."""
        stats = simulator.get_latency_stats()
        
        assert stats == {}

    def test_reset(self, simulator, market_data):
        """Test simulator reset."""
        # Generate some data
        for _ in range(50):
            simulator.sample_latency()
        simulator.simulate_fill(100.0, 1000, 5000, 0.02, 0.5)
        simulator.record_validation(100.0, 100.05, 0.5)
        
        # Reset
        simulator.reset()
        
        assert len(simulator._latency_samples) == 0
        assert len(simulator._fill_history) == 0
        assert len(simulator._validation_samples) == 0

    def test_batch_simulate_fills(self, simulator):
        """Test batch fill simulation."""
        orders = [
            {"size": 1000, "side": "buy", "arrival_price": 100.0},
            {"size": 500, "side": "sell", "arrival_price": 100.1},
            {"size": 2000, "side": "buy", "arrival_price": 100.2},
        ]
        market_data = {
            "queue_depth": 10000,
            "volatility": 0.02,
            "spread": 0.5,
        }
        
        fills = simulator.batch_simulate_fills(orders, market_data)
        
        assert len(fills) == 3
        assert all(isinstance(f, SimulatedFill) for f in fills)

    def test_reproducibility_with_seed(self, market_data):
        """Test that results are reproducible with same seed."""
        sim1 = TickLevelMarketSimulator(TickSimulatorConfig(seed=42))
        sim2 = TickLevelMarketSimulator(TickSimulatorConfig(seed=42))
        
        fill1 = sim1.simulate_fill(100.0, 1000, 5000, 0.02, 0.5, "buy")
        fill2 = sim2.simulate_fill(100.0, 1000, 5000, 0.02, 0.5, "buy")
        
        assert fill1.fill_price == fill2.fill_price
        assert fill1.latency_ms == fill2.latency_ms
        assert fill1.slippage == fill2.slippage

    def test_different_seeds_produce_different_results(self):
        """Test that different seeds produce different results."""
        sim1 = TickLevelMarketSimulator(TickSimulatorConfig(seed=42))
        sim2 = TickLevelMarketSimulator(TickSimulatorConfig(seed=123))
        
        # Generate multiple fills to see variation
        fills1 = []
        fills2 = []
        for i in range(20):
            f1 = sim1.simulate_fill(100.0, 1000 + i * 100, 5000, 0.02, 0.5, "buy")
            f2 = sim2.simulate_fill(100.0, 1000 + i * 100, 5000, 0.02, 0.5, "buy")
            fills1.append(f1)
            fills2.append(f2)
        
        # At least some should be different
        prices1 = [f.fill_price for f in fills1]
        prices2 = [f.fill_price for f in fills2]
        
        # Check that there's at least some variation
        assert prices1 != prices2 or [f.latency_ms for f in fills1] != [f.latency_ms for f in fills2]


class TestSimulatedFill:
    """Tests for SimulatedFill data structure."""

    def test_fill_creation(self):
        """Test creating a SimulatedFill."""
        fill = SimulatedFill(
            fill_price=100.5,
            latency_ms=15.3,
            slippage=0.05,
            spread_at_fill=0.5,
            queue_depth_at_fill=5000,
            timestamp=datetime(2026, 5, 22, 10, 0, 0, tzinfo=timezone.utc),
        )
        
        assert fill.fill_price == 100.5
        assert fill.latency_ms == 15.3
        assert fill.fill_id is not None
        assert len(fill.fill_id) == 16  # First 16 chars of SHA-256

    def test_fill_auto_id(self):
        """Test that fill ID is auto-generated."""
        fill1 = SimulatedFill(fill_price=100.0, latency_ms=10.0, slippage=0.01,
                             spread_at_fill=0.5, queue_depth_at_fill=5000,
                             timestamp=datetime(2026, 5, 22, 10, 0, 0, tzinfo=timezone.utc))
        fill2 = SimulatedFill(fill_price=100.0, latency_ms=10.0, slippage=0.01,
                             spread_at_fill=0.5, queue_depth_at_fill=5000,
                             timestamp=datetime(2026, 5, 22, 10, 0, 0, tzinfo=timezone.utc))
        
        assert fill1.fill_id == fill2.fill_id  # Same inputs = same ID
