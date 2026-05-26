"""
unified_strategy_runner.py — Same strategy code in backtest, paper, and live.
K211-K213: Unified execution context, mode-aware fill, deterministic replay.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
import json


class ExecutionMode(str, Enum):
    BACKTEST = "backtest"
    PAPER = "paper"
    LIVE = "live"


@dataclass
class ExecutionContext:
    mode: ExecutionMode = ExecutionMode.BACKTEST
    symbol: str = ""
    timestamp: Optional[datetime] = None
    current_price: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    volume: float = 0.0
    slippage_model: Optional[Callable] = None
    fee_model: Optional[Callable] = None
    latency_ms: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TradeResult:
    symbol: str = ""
    side: str = ""
    size: float = 0.0
    entry_price: float = 0.0
    exit_price: float = 0.0
    pnl: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    duration_seconds: float = 0.0
    mode: ExecutionMode = ExecutionMode.BACKTEST
    timestamp: Optional[datetime] = None


class UnifiedStrategyRunner:
    """
    Birlestirilmis strateji kosucu. Ayni strateji kodu
    backtest, paper ve live'da kosar.
    """

    def __init__(
        self,
        strategy_logic: Callable[[ExecutionContext, Dict], Dict],
        mode: ExecutionMode = ExecutionMode.BACKTEST,
        slippage_model: Optional[Callable] = None,
        fee_model: Optional[Callable] = None,
        on_trade: Optional[Callable] = None,
    ):
        self.strategy_logic = strategy_logic
        self.mode = mode
        self.slippage_model = slippage_model
        self.fee_model = fee_model
        self.on_trade = on_trade
        self._state: Dict[str, Any] = {}
        self._trades: List[TradeResult] = []
        self._positions: Dict[str, dict] = {}

    def run(self, ctx: ExecutionContext, params: Optional[Dict] = None) -> Dict:
        ctx.mode = self.mode
        if ctx.timestamp is None:
            ctx.timestamp = datetime.now(timezone.utc)
        ctx.slippage_model = self.slippage_model
        ctx.fee_model = self.fee_model

        signal = self.strategy_logic(ctx, params or {})

        if signal and signal.get("action") in ("BUY", "SELL"):
            return self._execute(ctx, signal)
        return {"action": "HOLD", "mode": self.mode.value}

    def _execute(self, ctx: ExecutionContext, signal: Dict) -> Dict:
        side = signal["action"]
        size = signal.get("size", 0)
        price = ctx.current_price

        if self.slippage_model:
            price = self.slippage_model(price, ctx)

        commission = 0.0
        if self.fee_model:
            commission = self.fee_model(size, price)

        symbol = ctx.symbol
        now = ctx.timestamp or datetime.now(timezone.utc)

        if side == "BUY":
            self._positions[symbol] = {
                "side": "long",
                "size": size,
                "entry_price": price,
                "entry_time": now,
            }
        elif side == "SELL" and symbol in self._positions:
            pos = self._positions[symbol]
            entry = pos["entry_price"]
            pnl = (price - entry) * pos["size"] - commission
            if pos["side"] == "short":
                pnl = (entry - price) * pos["size"] - commission

            duration = (now - pos["entry_time"]).total_seconds()
            result = TradeResult(
                symbol=symbol,
                side=pos["side"],
                size=pos["size"],
                entry_price=entry,
                exit_price=price,
                pnl=pnl,
                commission=commission,
                slippage=0.0,
                duration_seconds=duration,
                mode=self.mode,
                timestamp=now,
            )
            self._trades.append(result)
            if self.on_trade:
                self.on_trade(result)
            del self._positions[symbol]

        return {
            "action": side,
            "symbol": symbol,
            "price": price,
            "size": size,
            "commission": commission,
            "mode": self.mode.value,
        }

    def get_trades(self) -> List[TradeResult]:
        return self._trades.copy()

    def get_positions(self) -> Dict[str, dict]:
        return self._positions.copy()

    def reset(self):
        self._state.clear()
        self._trades.clear()
        self._positions.clear()

    def get_summary(self) -> Dict:
        if not self._trades:
            return {"total_trades": 0, "net_pnl": 0.0, "win_rate": 0.0}
        total = len(self._trades)
        wins = sum(1 for t in self._trades if t.pnl > 0)
        net_pnl = sum(t.pnl for t in self._trades)
        return {
            "total_trades": total,
            "net_pnl": net_pnl,
            "win_rate": wins / total if total else 0.0,
            "avg_duration_sec": sum(t.duration_seconds for t in self._trades) / total,
        }
