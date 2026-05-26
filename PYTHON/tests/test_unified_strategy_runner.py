"""
test_unified_strategy_runner.py — Tests for UnifiedStrategyRunner (K211-K213)
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from execution.unified_strategy_runner import (
    UnifiedStrategyRunner, ExecutionMode, ExecutionContext, TradeResult
)


def dummy_strategy(ctx, params):
    if ctx.current_price > params.get("threshold", 100):
        return {"action": "BUY", "size": 10}
    if ctx.current_price < params.get("low", 50):
        return {"action": "SELL", "size": 10}
    return {"action": "HOLD"}


class TestUnifiedStrategyRunner:
    def test_backtest_execution(self):
        runner = UnifiedStrategyRunner(strategy_logic=dummy_strategy, mode=ExecutionMode.BACKTEST)
        ctx = ExecutionContext(symbol="THYAO", current_price=150)
        result = runner.run(ctx, params={"threshold": 100})
        assert result["action"] == "BUY"
        assert result["mode"] == "backtest"

    def test_paper_execution(self):
        runner = UnifiedStrategyRunner(strategy_logic=dummy_strategy, mode=ExecutionMode.PAPER)
        ctx = ExecutionContext(symbol="THYAO", current_price=150)
        result = runner.run(ctx, params={"threshold": 100})
        assert result["mode"] == "paper"

    def test_sell_closes_position(self):
        runner = UnifiedStrategyRunner(strategy_logic=dummy_strategy, mode=ExecutionMode.BACKTEST)
        ctx = ExecutionContext(symbol="THYAO", current_price=150)
        runner.run(ctx, params={"threshold": 100})
        ctx.current_price = 40
        result = runner.run(ctx, params={"low": 50})
        assert result["action"] == "SELL"
        trades = runner.get_trades()
        assert len(trades) == 1
        assert trades[0].symbol == "THYAO"

    def test_slippage_model(self):
        def slippage(price, ctx):
            return price * 1.01
        runner = UnifiedStrategyRunner(strategy_logic=dummy_strategy, mode=ExecutionMode.BACKTEST, slippage_model=slippage)
        ctx = ExecutionContext(symbol="THYAO", current_price=150)
        result = runner.run(ctx, params={"threshold": 100})
        assert result["price"] == 150 * 1.01

    def test_fee_model(self):
        def fee(size, price):
            return size * price * 0.001
        runner = UnifiedStrategyRunner(strategy_logic=dummy_strategy, mode=ExecutionMode.BACKTEST, fee_model=fee)
        ctx = ExecutionContext(symbol="THYAO", current_price=150)
        result = runner.run(ctx, params={"threshold": 100})
        assert result["commission"] == 10 * 150 * 0.001

    def test_summary(self):
        runner = UnifiedStrategyRunner(strategy_logic=dummy_strategy, mode=ExecutionMode.BACKTEST)
        ctx = ExecutionContext(symbol="THYAO", current_price=150)
        runner.run(ctx, params={"threshold": 100})
        ctx.current_price = 40
        runner.run(ctx, params={"low": 50})
        summary = runner.get_summary()
        assert summary["total_trades"] == 1

    def test_reset(self):
        runner = UnifiedStrategyRunner(strategy_logic=dummy_strategy, mode=ExecutionMode.BACKTEST)
        ctx = ExecutionContext(symbol="THYAO", current_price=150)
        runner.run(ctx, params={"threshold": 100})
        runner.reset()
        assert len(runner.get_trades()) == 0
        assert len(runner.get_positions()) == 0

    def test_no_signal_hold(self):
        runner = UnifiedStrategyRunner(strategy_logic=dummy_strategy, mode=ExecutionMode.BACKTEST)
        ctx = ExecutionContext(symbol="THYAO", current_price=75)
        result = runner.run(ctx, params={"threshold": 100, "low": 50})
        assert result["action"] == "HOLD"
