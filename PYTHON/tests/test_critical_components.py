"""
PYTHON/tests/test_critical_components.py — Tests for Missing Critical Components

Tests for:
- Real-Time PnL Engine
- Margin Monitor
- Position Reconciliation
- Execution Algorithms
- Greeks Engine
"""
import pytest
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add PYTHON to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestRealTimePnLEngine:
    """Real-Time PnL Engine tests."""
    
    def test_pnl_engine_creation(self):
        from risk.real_time_pnl import RealTimePnLEngine
        engine = RealTimePnLEngine()
        assert engine is not None
    
    def test_record_realized_pnl(self, tmp_path):
        from risk.real_time_pnl import RealTimePnLEngine
        engine = RealTimePnLEngine(persistence_path=str(tmp_path / "pnl.json"))
        
        record = engine.record_realized_pnl(
            symbol="THYAO",
            strategy_id="test_strategy",
            pnl=1500.0,
            position_size=100,
            entry_price=100.0,
            exit_price=115.0,
            fees=5.0,
            slippage=2.0
        )
        
        assert record.pnl == 1500.0
        assert record.symbol == "THYAO"
        assert record.pnl_type.value == "realized"
    
    def test_unrealized_pnl_long(self, tmp_path):
        from risk.real_time_pnl import RealTimePnLEngine
        engine = RealTimePnLEngine(persistence_path=str(tmp_path / "pnl.json"))
        
        engine.update_position("GARAN", 100, 50.0, 50.0)
        unrealized = engine.calculate_unrealized_pnl("GARAN", 55.0)
        
        assert unrealized == 500.0  # (55-50) * 100
    
    def test_unrealized_pnl_short(self, tmp_path):
        from risk.real_time_pnl import RealTimePnLEngine
        engine = RealTimePnLEngine(persistence_path=str(tmp_path / "pnl.json"))
        
        engine.update_position("AKBNK", -100, 80.0, 80.0)
        unrealized = engine.calculate_unrealized_pnl("AKBNK", 75.0)
        
        assert unrealized == 500.0  # (80-75) * 100
    
    def test_pnl_summary(self, tmp_path):
        from risk.real_time_pnl import RealTimePnLEngine
        engine = RealTimePnLEngine(persistence_path=str(tmp_path / "pnl.json"))
        
        # Add some trades
        engine.record_realized_pnl("THYAO", "strat1", 1000.0, 100, 100.0, 110.0)
        engine.record_realized_pnl("GARAN", "strat1", -500.0, 100, 50.0, 45.0)
        
        summary = engine.get_pnl_summary('daily')
        
        assert summary.total_trades == 2
        assert summary.total_pnl == 500.0
        assert summary.winning_trades == 1
        assert summary.losing_trades == 1


class TestMarginMonitor:
    """Margin Monitor tests."""
    
    def test_margin_monitor_creation(self):
        from risk.margin_monitor import MarginMonitor
        monitor = MarginMonitor(initial_equity=100000.0)
        assert monitor is not None
    
    def test_margin_level_safe(self):
        from risk.margin_monitor import MarginMonitor, MarginLevel
        monitor = MarginMonitor(initial_equity=100000.0)
        
        monitor.update_position("THYAO", 100, 100.0, 100.0, leverage=2.0)
        
        margin_level = monitor.get_margin_level()
        status = monitor.get_margin_level_status(margin_level)
        
        assert margin_level > 150  # Should be safe
        assert status == MarginLevel.SAFE
    
    def test_liquidation_price_calculation(self):
        from risk.margin_monitor import MarginMonitor
        monitor = MarginMonitor(initial_equity=100000.0)
        
        monitor.set_exchange_margin_requirement("THYAO", 0.1)
        
        # Long position: liquidation below entry
        pos_long = monitor.update_position("THYAO", 100, 100.0, 100.0, leverage=10.0)
        liq_long = pos_long.liquidation_price
        
        # Short position: liquidation above entry
        pos_short = monitor.update_position("GARAN", -100, 100.0, 100.0, leverage=10.0)
        liq_short = pos_short.liquidation_price
        
        # Liquidation prices should be calculated (non-zero)
        assert liq_long > 0
        assert liq_short > 0
    
    def test_liquidation_risk(self):
        from risk.margin_monitor import MarginMonitor
        monitor = MarginMonitor(initial_equity=100000.0)
        
        # No positions = no risk
        risk = monitor.get_liquidation_risk()
        assert risk == 0.0
    
    def test_auto_deleveraging(self):
        from risk.margin_monitor import MarginMonitor
        monitor = MarginMonitor(initial_equity=100000.0)
        
        # Add large position
        monitor.update_position("THYAO", 1000, 100.0, 100.0, leverage=10.0)
        
        result = monitor.check_auto_deleveraging()
        
        # Should recommend deleveraging if margin level is low
        assert result is None or result.get('action') == 'deleveraging_required'


class TestPositionReconciliation:
    """Position Reconciliation Engine tests."""
    
    def test_reconciliation_engine_creation(self):
        from risk.position_reconciliation import PositionReconciliationEngine
        engine = PositionReconciliationEngine()
        assert engine is not None
    
    def test_matching_positions(self):
        from risk.position_reconciliation import PositionReconciliationEngine
        engine = PositionReconciliationEngine()
        
        # Update exchange position
        engine.update_exchange_position("THYAO", {
            'size': 100.0,
            'side': 'LONG',
            'entry_price': 100.0
        })
        
        # Reconcile with matching internal position
        result = engine.reconcile_position("THYAO", {
            'size': 100.0,
            'side': 'LONG',
            'entry_price': 100.0
        })
        
        assert result.matched == True
        assert len(result.discrepancies) == 0
    
    def test_size_mismatch(self):
        from risk.position_reconciliation import PositionReconciliationEngine, DiscrepancyType
        engine = PositionReconciliationEngine(tolerance_pct=1.0)
        
        engine.update_exchange_position("THYAO", {
            'size': 100.0,
            'side': 'LONG',
            'entry_price': 100.0
        })
        
        result = engine.reconcile_position("THYAO", {
            'size': 120.0,  # 20% difference
            'side': 'LONG',
            'entry_price': 100.0
        })
        
        assert result.matched == False
        assert any(d.discrepancy_type == DiscrepancyType.SIZE_MISMATCH for d in result.discrepancies)
    
    def test_orphan_position(self):
        from risk.position_reconciliation import PositionReconciliationEngine, DiscrepancyType
        engine = PositionReconciliationEngine()
        
        # Exchange has position, internal doesn't
        engine.update_exchange_position("THYAO", {
            'size': 100.0,
            'side': 'LONG',
            'entry_price': 100.0
        })
        
        result = engine.reconcile_position("THYAO", {
            'size': 0.0,
            'side': 'FLAT',
            'entry_price': 0.0
        })
        
        assert result.matched == False
        assert any(d.discrepancy_type == DiscrepancyType.ORPHAN_POSITION for d in result.discrepancies)
    
    def test_reconciliation_stats(self):
        from risk.position_reconciliation import PositionReconciliationEngine
        engine = PositionReconciliationEngine()
        
        stats = engine.get_reconciliation_stats()
        
        assert 'total_discrepancies' in stats
        assert 'resolved' in stats
        assert 'resolution_rate' in stats


class TestExecutionAlgorithms:
    """Execution Algorithms tests."""
    
    def test_twap_executor(self):
        from risk.execution_algorithms import TWAPExecutor
        executor = TWAPExecutor(duration_minutes=60, num_slices=12)
        
        slices = executor.generate_slices("THYAO", "BUY", 1200.0, "parent_123")
        
        assert len(slices) == 12
        assert all(s.size == 100.0 for s in slices)
    
    def test_vwap_executor(self):
        from risk.execution_algorithms import VWAPExecutor
        volume_profile = [1, 2, 3, 4, 3, 2, 1]  # Typical volume profile
        executor = VWAPExecutor(volume_profile=volume_profile)
        
        slices = executor.generate_slices("THYAO", "BUY", 1600.0, "parent_123")
        
        assert len(slices) == 7
        # First slice should be smallest (1/16 of total)
        assert slices[0].size == 100.0
    
    def test_iceberg_executor(self):
        from risk.execution_algorithms import IcebergExecutor
        executor = IcebergExecutor(visible_size=100)
        
        slices = executor.generate_slices("THYAO", "BUY", 350.0, "parent_123", 100.0)
        
        assert len(slices) == 4  # 100 + 100 + 100 + 50
        assert all(s.price == 100.0 for s in slices)
    
    def test_institutional_execution_engine(self):
        from risk.execution_algorithms import InstitutionalExecutionEngine
        engine = InstitutionalExecutionEngine()
        
        parent_id = engine.create_execution("twap", "THYAO", "BUY", 1200.0, duration_minutes=60)
        
        assert parent_id is not None
        
        orders = engine.get_active_orders(parent_id)
        assert len(orders) == 12


class TestGreeksEngine:
    """Greeks Engine tests."""
    
    def test_greeks_engine_creation(self):
        from risk.greeks_engine import GreeksEngine
        engine = GreeksEngine()
        assert engine is not None
    
    def test_call_option_greeks(self):
        from risk.greeks_engine import GreeksEngine, OptionPosition, OptionType
        from datetime import datetime, timezone, timedelta
        
        engine = GreeksEngine()
        
        # Add ITM call option
        expiry = datetime.now(timezone.utc) + timedelta(days=30)
        position = OptionPosition(
            symbol="THYAO240621C00100000",
            option_type=OptionType.CALL,
            strike=100.0,
            expiry=expiry,
            underlying_price=105.0,
            quantity=1,
            entry_price=8.0,
            current_price=9.0,
            implied_volatility=0.3,
            risk_free_rate=0.05
        )
        
        engine.add_position(position)
        greeks = engine.get_position_greeks(position.symbol)
        
        assert greeks is not None
        assert 0 < greeks.delta < 1  # ITM call delta
        assert greeks.gamma > 0
        assert greeks.theta < 0  # Time decay
        assert greeks.vega > 0
    
    def test_put_option_greeks(self):
        from risk.greeks_engine import GreeksEngine, OptionPosition, OptionType
        from datetime import datetime, timezone, timedelta
        
        engine = GreeksEngine()
        
        # Add OTM put option
        expiry = datetime.now(timezone.utc) + timedelta(days=30)
        position = OptionPosition(
            symbol="THYAO240621P00090000",
            option_type=OptionType.PUT,
            strike=90.0,
            expiry=expiry,
            underlying_price=105.0,
            quantity=1,
            entry_price=1.0,
            current_price=0.8,
            implied_volatility=0.3,
            risk_free_rate=0.05
        )
        
        engine.add_position(position)
        greeks = engine.get_position_greeks(position.symbol)
        
        assert greeks is not None
        assert -1 < greeks.delta < 0  # OTM put delta
        assert greeks.gamma > 0
    
    def test_portfolio_greeks(self):
        from risk.greeks_engine import GreeksEngine, OptionPosition, OptionType
        from datetime import datetime, timezone, timedelta
        
        engine = GreeksEngine()
        
        expiry = datetime.now(timezone.utc) + timedelta(days=30)
        
        # Add call
        call = OptionPosition(
            symbol="THYAO240621C00100000",
            option_type=OptionType.CALL,
            strike=100.0,
            expiry=expiry,
            underlying_price=105.0,
            quantity=1,
            entry_price=8.0,
            current_price=9.0,
            implied_volatility=0.3
        )
        
        # Add put (hedge)
        put = OptionPosition(
            symbol="THYAO240621P00100000",
            option_type=OptionType.PUT,
            strike=100.0,
            expiry=expiry,
            underlying_price=105.0,
            quantity=1,
            entry_price=3.0,
            current_price=2.5,
            implied_volatility=0.3
        )
        
        engine.add_position(call)
        engine.add_position(put)
        
        portfolio = engine.get_portfolio_greeks()
        
        assert portfolio.total_delta is not None
        assert portfolio.total_gamma is not None
        assert portfolio.total_theta is not None
        assert portfolio.total_vega is not None
    
    def test_hedging_recommendation(self):
        from risk.greeks_engine import GreeksEngine, OptionPosition, OptionType
        from datetime import datetime, timezone, timedelta
        
        engine = GreeksEngine()
        
        expiry = datetime.now(timezone.utc) + timedelta(days=30)
        
        # Add large call position (high delta)
        call = OptionPosition(
            symbol="THYAO240621C00100000",
            option_type=OptionType.CALL,
            strike=100.0,
            expiry=expiry,
            underlying_price=105.0,
            quantity=10,
            entry_price=8.0,
            current_price=9.0,
            implied_volatility=0.3
        )
        
        engine.add_position(call)
        recommendation = engine.get_hedging_recommendation(target_delta=0.0)
        
        assert recommendation['action'] in ['hedge_required', 'no_action']
        if recommendation['action'] == 'hedge_required':
            assert 'hedge_shares' in recommendation
            assert 'hedge_direction' in recommendation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

