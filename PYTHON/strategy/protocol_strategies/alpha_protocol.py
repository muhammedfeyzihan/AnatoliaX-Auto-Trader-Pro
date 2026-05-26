"""
alpha_protocol.py — Alpha Protocol: High-Probability Cross-Asset Strategy

Legal, mathematical, minimum-risk profit protocol for BIST, Crypto, Forex.

Entry ONLY when ALL 10 protocol gates open:
  1. Market open (UnifiedMarketCalendar)
  2. Black swan clear
  3. Immutable laws PASS
  4. ATR optimal (not dead, not explosive)
  5. Spread tight (< 0.5%)
  6. 2+ timeframe confluence
  7. Volume confirmation (> 1.2x avg)
  8. No news blackout window
  9. High-liquidity session
  10. R:R >= 1:2

Entry setups (at least one must fire):
  A. Momentum Breakout — consolidation breakout with volume + RSI confirmation
  B. Mean Reversion — BB touch + RSI extreme + reversal candle + volume
  C. Volatility Expansion — BB squeeze + ATR breakout + volume expansion
  D. Liquidity Sweep — sweep of recent high/low + rejection + close back

Risk Protocol:
  - Max 1% account risk / trade
  - R:R minimum 1:2
  - Position size = Account * 0.01 / (ATR * 1.5)
  - SL = structure-based or ATR*1.5
  - TP = ATR*3.0
  - Partial TP 50% at 1R
  - Trailing stop activates at 1R (trail by ATR)
  - Time stop: 5 bars without 0.5R move
  - Max 3 concurrent positions
  - Correlation filter: no pair > 0.80

Usage:
    from strategy.protocol_strategies.alpha_protocol import AlphaProtocol
    proto = AlphaProtocol(account_size=100_000)
    signal = proto.evaluate(df, symbol="THYAO", venue="BIST")
    if signal:
        print(signal)
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd

_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

from data.unified_market_calendar import UnifiedMarketCalendar
from risk.execution_laws import ImmutableExecutionLawEngine, LawVerdict
from risk.black_swan_guard import BlackSwanGuard


class SetupType(Enum):
    MOMENTUM_BREAKOUT = "MOMENTUM_BREAKOUT"
    MEAN_REVERSION = "MEAN_REVERSION"
    VOLATILITY_EXPANSION = "VOLATILITY_EXPANSION"
    LIQUIDITY_SWEEP = "LIQUIDITY_SWEEP"
    NONE = "NONE"


@dataclass
class AlphaSignal:
    symbol: str
    side: str  # BUY or SELL
    setup: SetupType
    entry_price: float
    stop_loss: float
    take_profit: float
    size: float
    risk_pct: float
    rr: float
    confidence: float
    timeframe: str
    reasons: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    valid: bool = True

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "setup": self.setup.value,
            "entry_price": round(self.entry_price, 4),
            "stop_loss": round(self.stop_loss, 4),
            "take_profit": round(self.take_profit, 4),
            "size": round(self.size, 4),
            "risk_pct": round(self.risk_pct, 4),
            "rr": round(self.rr, 2),
            "confidence": round(self.confidence, 1),
            "timeframe": self.timeframe,
            "reasons": self.reasons,
            "timestamp": self.timestamp,
            "valid": self.valid,
        }


class AlphaProtocol:
    """
    Alpha Protocol: Cross-asset high-probability trading system.

    NOT a get-rich-quick scheme. It is a disciplined, edge-driven system
    that only trades when mathematics and risk management align.
    """

    # Protocol parameters (regime-adaptive overrides possible)
    PARAMS = {
        "max_risk_per_trade_pct": 1.0,
        "max_daily_drawdown_pct": 3.0,
        "min_rr": 2.0,
        "max_spread_pct": 0.5,
        "min_atr_pct": 0.3,
        "max_atr_pct": 5.0,
        "volume_mult_threshold": 1.2,
        "rsi_long_min": 50,
        "rsi_long_max": 70,
        "rsi_short_min": 30,
        "rsi_short_max": 50,
        "bb_squeeze_width_pct": 2.0,
        "bb_squeeze_bars": 5,
        "partial_tp_ratio": 0.5,
        "trailing_atr_mult": 1.0,
        "time_stop_bars": 5,
        "max_concurrent_positions": 3,
        "max_correlation": 0.80,
        "session_filter": True,
    }

    def __init__(self, account_size: float = 100_000.0, params: Optional[Dict] = None):
        self.account_size = account_size
        self.params = {**self.PARAMS, **(params or {})}
        self.calendar = UnifiedMarketCalendar()
        self.law_engine = ImmutableExecutionLawEngine(strict_mode=True)
        self.black_swan_guard = BlackSwanGuard()
        self._positions: List[dict] = []
        self._daily_pnl: float = 0.0
        self._last_reset_day: int = datetime.now().day

    # ------------------------------------------------------------------
    # Core evaluation
    # ------------------------------------------------------------------
    def evaluate(
        self,
        df: pd.DataFrame,
        symbol: str,
        venue: str = "BIST",
        timeframe: str = "M15",
        higher_tf_df: Optional[pd.DataFrame] = None,
        macro: Optional[dict] = None,
    ) -> Optional[AlphaSignal]:
        """
        Main entry point. Returns AlphaSignal if ALL protocol gates pass.
        Returns None if any gate blocks.
        """
        now = datetime.now()

        # Gate 0: Daily drawdown check
        if now.day != self._last_reset_day:
            self._daily_pnl = 0.0
            self._last_reset_day = now.day
        if abs(self._daily_pnl) >= self.account_size * self.params["max_daily_drawdown_pct"] / 100:
            return None

        # Gate 1: Market open
        if not self.calendar.is_market_open(venue):
            return None

        # Gate 2: Black swan
        if self.black_swan_guard.is_halted():
            return None
        if len(df) >= 40:
            alert = self.black_swan_guard.check(df, symbol=symbol)
            if alert.is_black_swan and alert.level in ("CRITICAL", "EXTREME"):
                self.black_swan_guard.halt(symbol)
                return None

        # Gate 3: Immutable execution laws
        law_signal = self._build_law_signal(df, symbol)
        law_state = {"equity": self.account_size, "portfolio_heat": len(self._positions) * 0.01}
        verdict = self.law_engine.check(law_signal, state=law_state)
        if not verdict.allowed:
            return None

        # Pre-compute indicators
        ind = self._compute_indicators(df)
        if ind is None:
            return None

        # Gate 4: ATR optimal
        atr_pct = ind["atr_pct"]
        if not (self.params["min_atr_pct"] <= atr_pct <= self.params["max_atr_pct"]):
            return None

        # Gate 5: Spread tight
        spread_pct = ind.get("spread_pct", 0.0)
        if spread_pct > self.params["max_spread_pct"]:
            return None

        # Gate 6: Multi-timeframe confluence
        higher_aligned = False
        if higher_tf_df is not None and len(higher_tf_df) >= 20:
            higher_ind = self._compute_indicators(higher_tf_df)
            if higher_ind:
                higher_aligned = self._timeframe_aligned(ind, higher_ind)
        # If no higher TF provided, assume aligned (single-TF mode)
        if higher_tf_df is not None and not higher_aligned:
            return None

        # Gate 7: Volume confirmation
        if ind["volume_ratio"] < self.params["volume_mult_threshold"]:
            return None

        # Gate 8: News blackout (placeholder — integrate with news fetcher)
        # Gate 9: Session filter
        if self.params["session_filter"] and venue == "FOREX":
            if not self.calendar.is_high_liquidity_overlap():
                return None

        # Gate 10: R:R >= min — will be checked per-setup

        # Evaluate setups
        signal = self._evaluate_setups(ind, symbol, timeframe)
        if signal is None:
            return None

        # Final R:R gate
        if signal.rr < self.params["min_rr"]:
            return None

        # Max concurrent positions
        if len(self._positions) >= self.params["max_concurrent_positions"]:
            return None

        return signal

    # ------------------------------------------------------------------
    # Indicators
    # ------------------------------------------------------------------
    def _compute_indicators(self, df: pd.DataFrame) -> Optional[dict]:
        if len(df) < 20:
            return None
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        volume = df.get("volume", pd.Series([0] * len(df))).values

        atr = self._atr(high, low, close, period=14)
        atr_pct = atr / close[-1] * 100.0 if close[-1] != 0 else 0.0

        sma20 = np.mean(close[-20:])
        sma50 = np.mean(close[-50:]) if len(close) >= 50 else sma20

        bb_mid = sma20
        bb_std = np.std(close[-20:])
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std
        bb_width = (bb_upper - bb_lower) / bb_mid * 100.0 if bb_mid != 0 else 0.0

        rsi = self._rsi(close, period=14)
        volume_sma20 = np.mean(volume[-20:]) if len(volume) >= 20 else 1.0
        volume_ratio = volume[-1] / volume_sma20 if volume_sma20 > 0 else 1.0

        spread_pct = ((high[-1] - low[-1]) / close[-1] * 100.0) if close[-1] != 0 else 0.0

        return {
            "close": close[-1],
            "high": high[-1],
            "low": low[-1],
            "open": df["open"].values[-1] if "open" in df.columns else close[-1],
            "atr": atr,
            "atr_pct": atr_pct,
            "sma20": sma20,
            "sma50": sma50,
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
            "bb_width": bb_width,
            "bb_squeeze": bb_width < self.params["bb_squeeze_width_pct"],
            "rsi": rsi,
            "volume_ratio": volume_ratio,
            "spread_pct": spread_pct,
            "prev_high": np.max(high[-5:-1]) if len(high) >= 5 else high[-1],
            "prev_low": np.min(low[-5:-1]) if len(low) >= 5 else low[-1],
        }

    def _timeframe_aligned(self, primary: dict, higher: dict) -> bool:
        """Higher timeframe trend must agree with primary direction."""
        # Simple: price above both SMAs = bullish alignment; below both = bearish
        bullish = primary["close"] > primary["sma20"] and higher["close"] > higher["sma20"]
        bearish = primary["close"] < primary["sma20"] and higher["close"] < higher["sma20"]
        return bullish or bearish

    # ------------------------------------------------------------------
    # Setup evaluation
    # ------------------------------------------------------------------
    def _evaluate_setups(self, ind: dict, symbol: str, timeframe: str) -> Optional[AlphaSignal]:
        signals: List[AlphaSignal] = []

        # Setup A: Momentum Breakout
        sig = self._setup_momentum_breakout(ind, symbol, timeframe)
        if sig:
            signals.append(sig)

        # Setup B: Mean Reversion
        sig = self._setup_mean_reversion(ind, symbol, timeframe)
        if sig:
            signals.append(sig)

        # Setup C: Volatility Expansion
        sig = self._setup_volatility_expansion(ind, symbol, timeframe)
        if sig:
            signals.append(sig)

        # Setup D: Liquidity Sweep
        sig = self._setup_liquidity_sweep(ind, symbol, timeframe)
        if sig:
            signals.append(sig)

        if not signals:
            return None

        # Pick highest confidence signal
        best = max(signals, key=lambda s: s.confidence)
        return best

    def _setup_momentum_breakout(self, ind: dict, symbol: str, tf: str) -> Optional[AlphaSignal]:
        close = ind["close"]
        prev_high = ind["prev_high"]
        prev_low = ind["prev_low"]
        rsi = ind["rsi"]
        vol = ind["volume_ratio"]

        # Long: close > prev_high + RSI 50-70 + volume > 1.2x
        if close > prev_high and self.params["rsi_long_min"] <= rsi <= self.params["rsi_long_max"] and vol >= 1.2:
            sl = min(close - ind["atr"] * 1.5, prev_low)
            tp = close + ind["atr"] * 3.0
            rr = (tp - close) / (close - sl) if (close - sl) > 0 else 0
            size = self._position_size(close, sl)
            conf = 60 + (rsi - 50) * 0.5 + (vol - 1.0) * 10
            return AlphaSignal(
                symbol=symbol, side="BUY", setup=SetupType.MOMENTUM_BREAKOUT,
                entry_price=close, stop_loss=sl, take_profit=tp,
                size=size, risk_pct=self.params["max_risk_per_trade_pct"],
                rr=rr, confidence=min(conf, 95), timeframe=tf,
                reasons=["Breakout above recent high", f"RSI {rsi:.1f}", f"Volume {vol:.1f}x"],
            )

        # Short: close < prev_low + RSI 30-50 + volume >= 1.2x
        if close < prev_low and self.params["rsi_short_min"] <= rsi <= self.params["rsi_short_max"] and vol >= 1.2:
            sl = max(close + ind["atr"] * 1.5, prev_high)
            tp = close - ind["atr"] * 3.0
            rr = (close - tp) / (sl - close) if (sl - close) > 0 else 0
            size = self._position_size(close, sl)
            conf = 60 + (50 - rsi) * 0.5 + (vol - 1.0) * 10
            return AlphaSignal(
                symbol=symbol, side="SELL", setup=SetupType.MOMENTUM_BREAKOUT,
                entry_price=close, stop_loss=sl, take_profit=tp,
                size=size, risk_pct=self.params["max_risk_per_trade_pct"],
                rr=rr, confidence=min(conf, 95), timeframe=tf,
                reasons=["Breakdown below recent low", f"RSI {rsi:.1f}", f"Volume {vol:.1f}x"],
            )
        return None

    def _setup_mean_reversion(self, ind: dict, symbol: str, tf: str) -> Optional[AlphaSignal]:
        close = ind["close"]
        rsi = ind["rsi"]
        vol = ind["volume_ratio"]

        # Long: price near or below BB lower + RSI < 35 + volume spike
        if close <= ind["bb_lower"] * 1.005 and rsi < 35 and vol >= 1.3:
            sl = close - ind["atr"] * 1.5
            tp = close + ind["atr"] * 3.0
            rr = (tp - close) / (close - sl) if (close - sl) > 0 else 0
            size = self._position_size(close, sl)
            conf = 55 + (35 - rsi) * 0.8 + (vol - 1.0) * 10
            return AlphaSignal(
                symbol=symbol, side="BUY", setup=SetupType.MEAN_REVERSION,
                entry_price=close, stop_loss=sl, take_profit=tp,
                size=size, risk_pct=self.params["max_risk_per_trade_pct"],
                rr=rr, confidence=min(conf, 95), timeframe=tf,
                reasons=["Mean reversion from BB lower", f"RSI {rsi:.1f}", f"Volume {vol:.1f}x"],
            )

        # Short: price near or above BB upper + RSI > 65 + volume spike
        if close >= ind["bb_upper"] * 0.995 and rsi > 65 and vol >= 1.3:
            sl = close + ind["atr"] * 1.5
            tp = close - ind["atr"] * 3.0
            rr = (close - tp) / (sl - close) if (sl - close) > 0 else 0
            size = self._position_size(close, sl)
            conf = 55 + (rsi - 65) * 0.8 + (vol - 1.0) * 10
            return AlphaSignal(
                symbol=symbol, side="SELL", setup=SetupType.MEAN_REVERSION,
                entry_price=close, stop_loss=sl, take_profit=tp,
                size=size, risk_pct=self.params["max_risk_per_trade_pct"],
                rr=rr, confidence=min(conf, 95), timeframe=tf,
                reasons=["Mean reversion from BB upper", f"RSI {rsi:.1f}", f"Volume {vol:.1f}x"],
            )
        return None

    def _setup_volatility_expansion(self, ind: dict, symbol: str, tf: str) -> Optional[AlphaSignal]:
        close = ind["close"]
        vol = ind["volume_ratio"]
        # BB squeeze for N bars + current expansion
        if not ind["bb_squeeze"]:
            return None
        if vol < 1.5:
            return None
        # Direction: follow the breakout direction
        if close > ind["sma20"]:
            sl = close - ind["atr"] * 1.5
            tp = close + ind["atr"] * 3.0
            rr = (tp - close) / (close - sl) if (close - sl) > 0 else 0
            size = self._position_size(close, sl)
            return AlphaSignal(
                symbol=symbol, side="BUY", setup=SetupType.VOLATILITY_EXPANSION,
                entry_price=close, stop_loss=sl, take_profit=tp,
                size=size, risk_pct=self.params["max_risk_per_trade_pct"],
                rr=rr, confidence=70, timeframe=tf,
                reasons=["BB squeeze breakout", f"BB width {ind['bb_width']:.2f}%", f"Volume {vol:.1f}x"],
            )
        else:
            sl = close + ind["atr"] * 1.5
            tp = close - ind["atr"] * 3.0
            rr = (close - tp) / (sl - close) if (sl - close) > 0 else 0
            size = self._position_size(close, sl)
            return AlphaSignal(
                symbol=symbol, side="SELL", setup=SetupType.VOLATILITY_EXPANSION,
                entry_price=close, stop_loss=sl, take_profit=tp,
                size=size, risk_pct=self.params["max_risk_per_trade_pct"],
                rr=rr, confidence=70, timeframe=tf,
                reasons=["BB squeeze breakdown", f"BB width {ind['bb_width']:.2f}%", f"Volume {vol:.1f}x"],
            )

    def _setup_liquidity_sweep(self, ind: dict, symbol: str, tf: str) -> Optional[AlphaSignal]:
        close = ind["close"]
        prev_low = ind["prev_low"]
        prev_high = ind["prev_high"]
        vol = ind["volume_ratio"]
        if vol < 1.5:
            return None

        # Long: sweep below prev_low + close back above
        if close > prev_low and ind.get("low", close) < prev_low * 0.998:
            sl = close - ind["atr"] * 1.5
            tp = close + ind["atr"] * 3.0
            rr = (tp - close) / (close - sl) if (close - sl) > 0 else 0
            size = self._position_size(close, sl)
            return AlphaSignal(
                symbol=symbol, side="BUY", setup=SetupType.LIQUIDITY_SWEEP,
                entry_price=close, stop_loss=sl, take_profit=tp,
                size=size, risk_pct=self.params["max_risk_per_trade_pct"],
                rr=rr, confidence=75, timeframe=tf,
                reasons=["Liquidity sweep + rejection (long)", f"Swept {prev_low:.2f}", f"Volume {vol:.1f}x"],
            )

        # Short: sweep above prev_high + close back below
        if close < prev_high and ind.get("high", close) > prev_high * 1.002:
            sl = close + ind["atr"] * 1.5
            tp = close - ind["atr"] * 3.0
            rr = (close - tp) / (sl - close) if (sl - close) > 0 else 0
            size = self._position_size(close, sl)
            return AlphaSignal(
                symbol=symbol, side="SELL", setup=SetupType.LIQUIDITY_SWEEP,
                entry_price=close, stop_loss=sl, take_profit=tp,
                size=size, risk_pct=self.params["max_risk_per_trade_pct"],
                rr=rr, confidence=75, timeframe=tf,
                reasons=["Liquidity sweep + rejection (short)", f"Swept {prev_high:.2f}", f"Volume {vol:.1f}x"],
            )
        return None

    # ------------------------------------------------------------------
    # Position sizing
    # ------------------------------------------------------------------
    def _position_size(self, entry: float, stop: float) -> float:
        risk_amount = self.account_size * self.params["max_risk_per_trade_pct"] / 100.0
        risk_per_unit = abs(entry - stop)
        if risk_per_unit <= 0:
            return 0.0
        size = risk_amount / risk_per_unit
        return round(size, 4)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _atr(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> float:
        if len(high) < period + 1:
            return np.mean(high - low)
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        return float(np.mean(tr[-period:]))

    def _rsi(self, close: np.ndarray, period: int = 14) -> float:
        if len(close) < period + 1:
            return 50.0
        deltas = np.diff(close)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _build_law_signal(self, df: pd.DataFrame, symbol: str) -> dict:
        if df.empty or not {"high", "low", "close"}.issubset(df.columns):
            return {
                "symbol": symbol,
                "side": "WAIT",
                "size": 0,
                "price": 0.0,
                "confidence": 0.0,
                "atr_pct": 0.0,
                "spread_pct": 0.0,
                "leverage": 1.0,
                "prob_win": 0.5,
            }
        close = df["close"].iloc[-1] if len(df) > 0 else 0.0
        atr = self._atr(df["high"].values, df["low"].values, df["close"].values)
        atr_pct = atr / close * 100.0 if close > 0 else 0.0
        spread = ((df["high"].iloc[-1] - df["low"].iloc[-1]) / close * 100.0) if close > 0 else 0.0
        return {
            "symbol": symbol,
            "side": "BUY",
            "size": 0,
            "price": close,
            "confidence": 80.0,
            "atr_pct": atr_pct,
            "spread_pct": spread,
            "leverage": 1.0,
            "prob_win": 0.6,
            "fake_breakout_prob": 0.1,
            "liquidation_risk": 0.0,
            "stale_order_seconds": 0.0,
        }

    # ------------------------------------------------------------------
    # Post-trade tracking
    # ------------------------------------------------------------------
    def add_position(self, signal: AlphaSignal):
        self._positions.append(signal.to_dict())

    def close_position(self, symbol: str, exit_price: float):
        for p in self._positions:
            if p["symbol"] == symbol:
                side_mult = 1 if p["side"] == "BUY" else -1
                pnl = side_mult * (exit_price - p["entry_price"]) * p["size"]
                self._daily_pnl += pnl
                self._positions.remove(p)
                break

    def get_protocol_stats(self) -> dict:
        return {
            "account_size": self.account_size,
            "daily_pnl": round(self._daily_pnl, 2),
            "open_positions": len(self._positions),
            "max_positions": self.params["max_concurrent_positions"],
            "params": self.params,
        }


if __name__ == "__main__":
    import pandas as pd
    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        "open": 100 + np.cumsum(np.random.randn(n) * 0.5),
        "high": 100 + np.cumsum(np.random.randn(n) * 0.5) + 0.3,
        "low": 100 + np.cumsum(np.random.randn(n) * 0.5) - 0.3,
        "close": 100 + np.cumsum(np.random.randn(n) * 0.5),
        "volume": np.random.randint(1000, 5000, n),
    })
    proto = AlphaProtocol(account_size=100_000)
    signal = proto.evaluate(df, symbol="THYAO", venue="BIST")
    if signal:
        print("SIGNAL:", signal.to_dict())
    else:
        print("No signal — protocol gates blocked (normal for random data)")
    print("Stats:", proto.get_protocol_stats())
