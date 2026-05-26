"""
manipulation_detector.py — Swarm-Based Market Manipulation Detection

Inspired by MiroFish parallel simulation + Ruflo behavioral trust scoring.

Detects:
- Spoofing / Layering: Fake orders placed then cancelled
- Wash Trading: Same entity buying and selling to itself
- Pump & Dump: Coordinated price + volume spike then crash
- Bear Raid: Coordinated selling to push price down
- Quote Stuffing: Rapid order flooding
- Momentum Ignition: Artificial momentum creation

Usage:
    from agents.manipulation_detector import ManipulationDetector
    det = ManipulationDetector()
    result = det.analyze(df, symbol="THYAO")
    if result.is_manipulated:
        print(f"ALERT: {result.pattern} detected (score: {result.score})")
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque


class ManipulationPattern(Enum):
    NONE = "NONE"
    SPOOFING = "SPOOFING"
    WASH_TRADING = "WASH_TRADING"
    PUMP_AND_DUMP = "PUMP_AND_DUMP"
    BEAR_RAID = "BEAR_RAID"
    QUOTE_STUFFING = "QUOTE_STUFFING"
    MOMENTUM_IGNITION = "MOMENTUM_IGNITION"
    FLASH_CRASH = "FLASH_CRASH"


@dataclass
class ManipulationResult:
    symbol: str
    is_manipulated: bool
    pattern: ManipulationPattern
    score: float  # 0-100
    confidence: float
    evidence: List[str] = field(default_factory=list)
    affected_candles: int = 0


class ManipulationDetector:
    """
    Multi-layer manipulation detection engine.

    Kural K261: Manipülasyon skoru > 70 olan sembolde emir verilmez.
    Kural K262: Pump&Dump tespiti sonrası 24 saat boyunca o sembolde alım yapılmaz.
    Kural K263: Wash trading tespiti sonrası ilgili borsa adaptörü devre dışı bırakılır.
    """

    def __init__(self, history_size: int = 1000):
        self.history_size = history_size
        self._tick_history: Dict[str, deque] = {}
        self._detection_log: List[dict] = []
        self._blocklist: Dict[str, float] = {}  # symbol -> unblock_time

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def analyze(self, df: pd.DataFrame, symbol: str) -> ManipulationResult:
        """Run all detection layers on a DataFrame."""
        if len(df) < 20:
            return ManipulationResult(symbol=symbol, is_manipulated=False, pattern=ManipulationPattern.NONE, score=0.0, confidence=0.0)
        
        # Normalize DataFrame: ensure OHLCV columns exist
        df = self._normalize_ohlcv(df)

        # Check blocklist
        if symbol in self._blocklist and pd.Timestamp.now().timestamp() < self._blocklist[symbol]:
            return ManipulationResult(
                symbol=symbol, is_manipulated=True,
                pattern=ManipulationPattern.PUMP_AND_DUMP,
                score=100.0, confidence=1.0,
                evidence=["Sembol blocklist'te (manipülasyon geçmişi)"],
            )

        results = []
        results.append(self._detect_spoofing(df, symbol))
        results.append(self._detect_wash_trading(df, symbol))
        results.append(self._detect_pump_and_dump(df, symbol))
        results.append(self._detect_bear_raid(df, symbol))
        results.append(self._detect_quote_stuffing(df, symbol))
        results.append(self._detect_momentum_ignition(df, symbol))

        # Pick highest score
        best = max(results, key=lambda r: r.score)
        if best.is_manipulated:
            self._detection_log.append({
                "time": pd.Timestamp.now().isoformat(),
                "symbol": symbol,
                "pattern": best.pattern.value,
                "score": best.score,
            })
            # Blocklist for pump&dump
            if best.pattern == ManipulationPattern.PUMP_AND_DUMP:
                self._blocklist[symbol] = pd.Timestamp.now().timestamp() + 86400

        return best
    
    def detect(self, df: pd.DataFrame) -> ManipulationResult:
        """Alias for analyze() - detect manipulation patterns."""
        return self.analyze(df, symbol="UNKNOWN")

    def is_blocked(self, symbol: str) -> bool:
        return symbol in self._blocklist and pd.Timestamp.now().timestamp() < self._blocklist[symbol]

    def get_blocklist(self) -> List[str]:
        now = pd.Timestamp.now().timestamp()
        return [s for s, t in self._blocklist.items() if now < t]

    def _normalize_ohlcv(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize DataFrame to ensure OHLCV columns exist."""
        result = df.copy()
        
        # If we have 'price' but not 'close', use 'price' as 'close'
        if 'close' not in result.columns and 'price' in result.columns:
            result['close'] = result['price']
        
        # If we don't have 'high'/'low', derive from 'close'
        if 'high' not in result.columns:
            result['high'] = result['close'] * 1.001
        if 'low' not in result.columns:
            result['low'] = result['close'] * 0.999
        
        if 'open' not in result.columns:
            result['open'] = result['close']
        
        return result

    # ------------------------------------------------------------------
    # Layer 1: Spoofing / Layering
    # ------------------------------------------------------------------
    def _detect_spoofing(self, df: pd.DataFrame, symbol: str) -> ManipulationResult:
        """
        Heuristic: Large bid-ask spread reversal + volume spike + no follow-through.
        """
        if "bid" not in df.columns or "ask" not in df.columns:
            return ManipulationResult(symbol, False, ManipulationPattern.SPOOFING, 0.0, 0.0)

        spread = (df["ask"] - df["bid"]) / ((df["ask"] + df["bid"]) / 2) * 100
        spread_z = (spread.iloc[-1] - spread.mean()) / spread.std() if spread.std() > 0 else 0
        vol_z = self._volume_zscore(df)

        score = 0.0
        evidence = []
        if spread_z > 3.0:
            score += 40
            evidence.append(f"Spread anomaly: z={spread_z:.1f}")
        if vol_z > 2.5:
            score += 30
            evidence.append(f"Volume spike: z={vol_z:.1f}")
        if len(df) >= 3 and abs(df["close"].iloc[-1] - df["close"].iloc[-3]) / df["close"].iloc[-3] * 100 < 0.5:
            score += 20
            evidence.append("No price follow-through")

        return ManipulationResult(
            symbol=symbol,
            is_manipulated=score >= 70,
            pattern=ManipulationPattern.SPOOFING,
            score=min(score, 100),
            confidence=min(score / 100, 1.0),
            evidence=evidence,
        )

    # ------------------------------------------------------------------
    # Layer 2: Wash Trading
    # ------------------------------------------------------------------
    def _detect_wash_trading(self, df: pd.DataFrame, symbol: str) -> ManipulationResult:
        """
        Heuristic: Volume spike + price flat + high trade count with no real movement.
        """
        if len(df) < 10:
            return ManipulationResult(symbol, False, ManipulationPattern.WASH_TRADING, 0.0, 0.0)

        returns = df["close"].pct_change().abs()
        vol = df.get("volume", pd.Series([0]*len(df)))
        vol_z = (vol.iloc[-1] - vol.mean()) / vol.std() if vol.std() > 0 else 0
        price_range = (df["high"] - df["low"]).iloc[-5:].mean()
        avg_price = df["close"].iloc[-5:].mean()
        range_pct = price_range / avg_price * 100 if avg_price > 0 else 0

        score = 0.0
        evidence = []
        if vol_z > 3.0:
            score += 40
            evidence.append(f"Volume anomaly: z={vol_z:.1f}")
        if returns.iloc[-5:].mean() < 0.001:  # < 0.1% avg return
            score += 30
            evidence.append("Flat price despite volume")
        if range_pct < 0.3:
            score += 20
            evidence.append(f"Tight range: {range_pct:.2f}%")

        return ManipulationResult(
            symbol=symbol, is_manipulated=score >= 70,
            pattern=ManipulationPattern.WASH_TRADING,
            score=min(score, 100), confidence=min(score/100, 1.0),
            evidence=evidence,
        )

    # ------------------------------------------------------------------
    # Layer 3: Pump & Dump
    # ------------------------------------------------------------------
    def _detect_pump_and_dump(self, df: pd.DataFrame, symbol: str) -> ManipulationResult:
        """
        Heuristic: Sharp rise (>5% in few candles) + volume explosion + immediate reversal.
        """
        if len(df) < 10:
            return ManipulationResult(symbol, False, ManipulationPattern.PUMP_AND_DUMP, 0.0, 0.0)

        close = df["close"]
        vol = df.get("volume", pd.Series([0]*len(df)))
        returns = close.pct_change() * 100

        # Look for spike then drop
        recent_returns = returns.iloc[-5:]
        max_up = recent_returns.max()
        max_down = recent_returns.min()
        vol_z = self._volume_zscore(df)

        score = 0.0
        evidence = []
        if max_up > 5.0:
            score += 40
            evidence.append(f"Sharp rise: +{max_up:.1f}%")
        if max_down < -3.0 and abs(max_down) > max_up * 0.5:
            score += 30
            evidence.append(f"Immediate reversal: {max_down:.1f}%")
        if vol_z > 2.5:
            score += 20
            evidence.append(f"Volume spike: z={vol_z:.1f}")
        # Check if price is back near start
        if len(close) >= 6 and abs(close.iloc[-1] - close.iloc[-6]) / close.iloc[-6] * 100 < 1.0:
            score += 10
            evidence.append("Price back to baseline")

        return ManipulationResult(
            symbol=symbol, is_manipulated=score >= 70,
            pattern=ManipulationPattern.PUMP_AND_DUMP,
            score=min(score, 100), confidence=min(score/100, 1.0),
            evidence=evidence,
        )

    # ------------------------------------------------------------------
    # Layer 4: Bear Raid
    # ------------------------------------------------------------------
    def _detect_bear_raid(self, df: pd.DataFrame, symbol: str) -> ManipulationResult:
        """
        Coordinated selling: sharp drop on high volume, then stabilization.
        """
        returns = df["close"].pct_change() * 100
        vol = df.get("volume", pd.Series([0]*len(df)))
        vol_z = self._volume_zscore(df)
        recent = returns.iloc[-5:]

        score = 0.0
        evidence = []
        if recent.min() < -5.0:
            score += 45
            evidence.append(f"Sharp drop: {recent.min():.1f}%")
        if vol_z > 2.5:
            score += 30
            evidence.append(f"High volume: z={vol_z:.1f}")
        if len(df) >= 3 and df["close"].iloc[-1] >= df["close"].iloc[-3]:
            score += 15
            evidence.append("Stabilization after drop")

        return ManipulationResult(
            symbol=symbol, is_manipulated=score >= 70,
            pattern=ManipulationPattern.BEAR_RAID,
            score=min(score, 100), confidence=min(score/100, 1.0),
            evidence=evidence,
        )

    # ------------------------------------------------------------------
    # Layer 5: Quote Stuffing
    # ------------------------------------------------------------------
    def _detect_quote_stuffing(self, df: pd.DataFrame, symbol: str) -> ManipulationResult:
        """
        Rapid order flooding: detected via volume-per-tick burst.
        """
        vol = df.get("volume", pd.Series([0]*len(df)))
        if len(vol) < 5:
            return ManipulationResult(symbol, False, ManipulationPattern.QUOTE_STUFFING, 0.0, 0.0)
        vol_z = self._volume_zscore(df)
        score = 0.0
        evidence = []
        if vol_z > 4.0:
            score += 60
            evidence.append(f"Extreme volume burst: z={vol_z:.1f}")
        if vol.iloc[-5:].std() / vol.iloc[-5:].mean() > 2.0:
            score += 20
            evidence.append("Volume volatility burst")
        return ManipulationResult(
            symbol=symbol, is_manipulated=score >= 70,
            pattern=ManipulationPattern.QUOTE_STUFFING,
            score=min(score, 100), confidence=min(score/100, 1.0),
            evidence=evidence,
        )

    # ------------------------------------------------------------------
    # Layer 6: Momentum Ignition
    # ------------------------------------------------------------------
    def _detect_momentum_ignition(self, df: pd.DataFrame, symbol: str) -> ManipulationResult:
        """
        Artificial momentum: small-cap stock suddenly surging with no news.
        """
        close = df["close"]
        returns = close.pct_change() * 100
        if len(returns) < 10:
            return ManipulationResult(symbol, False, ManipulationPattern.MOMENTUM_IGNITION, 0.0, 0.0)

        recent = returns.iloc[-5:]
        prior = returns.iloc[-10:-5]
        vol = df.get("volume", pd.Series([0]*len(df)))
        vol_z = self._volume_zscore(df)

        score = 0.0
        evidence = []
        if recent.mean() > 2.0 and prior.mean() < 0.5:
            score += 40
            evidence.append(f"Sudden momentum: {recent.mean():.1f}% vs prior {prior.mean():.1f}%")
        if vol_z > 2.0:
            score += 30
            evidence.append(f"Volume ignition: z={vol_z:.1f}")
        if len(close) >= 20 and close.iloc[-1] > close.iloc[-20:-5].max() * 1.05:
            score += 20
            evidence.append("Breakout from multi-candle range")

        return ManipulationResult(
            symbol=symbol, is_manipulated=score >= 70,
            pattern=ManipulationPattern.MOMENTUM_IGNITION,
            score=min(score, 100), confidence=min(score/100, 1.0),
            evidence=evidence,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _volume_zscore(self, df: pd.DataFrame) -> float:
        vol = df.get("volume", pd.Series([0]*len(df)))
        if vol.std() <= 0 or len(vol) < 5:
            return 0.0
        return float((vol.iloc[-1] - vol.mean()) / vol.std())


if __name__ == "__main__":
    # Simulate pump & dump
    close = [100.0] * 10 + [102.0, 105.0, 108.0, 106.0, 101.0, 100.5]
    df = pd.DataFrame({
        "open": close,
        "high": [c + 1 for c in close],
        "low": [c - 1 for c in close],
        "close": close,
        "volume": [1000] * 10 + [3000, 5000, 8000, 6000, 4000, 2000],
    })
    det = ManipulationDetector()
    res = det.analyze(df, symbol="TEST")
    print(f"Manipulated: {res.is_manipulated}, Pattern: {res.pattern.value}, Score: {res.score}")
    print("Evidence:", res.evidence)
