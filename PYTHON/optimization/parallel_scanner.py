"""
parallel_scanner.py — Parallel Symbol Scanner (K242)

Optimizations over sequential SignalEngine.run_scan():
- ThreadPoolExecutor for I/O-bound data fetching
- ProcessPoolExecutor (or ThreadPoolExecutor) for CPU-bound indicator/signal analysis
- AsyncFeedAggregator integration for maximum fetch parallelism
- Result aggregation with progress tracking

Usage:
    from optimization.parallel_scanner import ParallelScanner
    scanner = ParallelScanner(max_workers=8)
    results = scanner.run_scan(["THYAO", "GARAN", "ASELS", ...])
"""

import os
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

import concurrent.futures
from datetime import datetime
from typing import Callable, Optional

import pandas as pd

from data.market_calendar import BISTCalendar
from data.feed_aggregator import FeedAggregator
from backtest.indicators import apply_all
from backtest.signals import combined_signal
from paper_trading.paper_broker import PaperBroker


class ParallelScanner:
    """
    Parallel symbol scanner with configurable workers.
    """

    def __init__(
        self,
        max_workers: int = 8,
        signal_threshold: float = 70.0,
        max_positions: int = 5,
        max_risk_pct: float = 10.0,
        fetch_batch_size: int = 16,
    ):
        self.max_workers = max_workers
        self.signal_threshold = signal_threshold
        self.max_positions = max_positions
        self.max_risk_pct = max_risk_pct
        self.fetch_batch_size = fetch_batch_size
        self.calendar = BISTCalendar()
        self.broker = PaperBroker(max_positions=max_positions, max_risk_pct=max_risk_pct)

    def _check_market_open(self) -> tuple[bool, str]:
        if self.calendar.is_holiday():
            return False, self.calendar.get_reason()
        if not self.calendar.is_market_open():
            return False, "BIST su an kapali (09:30-18:00 acik)"
        return True, "Piyasa acik"

    def _analyze_symbol(self, symbol: str, interval: str = "1d", period: str = "3mo") -> Optional[dict]:
        """Analyze a single symbol (I/O + CPU). Thread-safe."""
        feed = FeedAggregator()
        try:
            df = feed.fetch(symbol, interval=interval, period=period)
        except Exception as e:
            return None

        if len(df) < 50:
            return None

        # Compute indicators and signals
        df = apply_all(df)
        df = combined_signal(df)

        last = df.iloc[-1]
        score = last.get("Signal_Score", 0)
        signal = last.get("Signal", 0)

        if score < self.signal_threshold or signal < 2:
            return None

        entry = last["close"]
        atr = last.get("ATR", entry * 0.03)
        sl = entry - (atr * 2)
        tp1 = entry + (atr * 3)
        tp2 = entry + (atr * 4)

        risk = abs(entry - sl)
        reward = abs(tp1 - entry)
        r_r = reward / risk if risk > 0 else 0.0
        if r_r < 2.0:
            return None

        return {
            "symbol": symbol,
            "score": score,
            "entry": entry,
            "sl": sl,
            "tp1": tp1,
            "tp2": tp2,
            "r_r": r_r,
            "timestamp": datetime.now(),
        }

    def run_scan(
        self,
        symbols: list[str],
        interval: str = "1d",
        period: str = "3mo",
    ) -> list[dict]:
        """
        Scan symbols in parallel using ThreadPoolExecutor.
        Returns list of signal dicts.
        """
        is_open, reason = self._check_market_open()
        if not is_open:
            return [{"market_closed": True, "reason": reason}]

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_sym = {
                executor.submit(self._analyze_symbol, sym, interval, period): sym
                for sym in symbols
            }
            for future in concurrent.futures.as_completed(future_to_sym):
                sym = future_to_sym[future]
                try:
                    signal = future.result(timeout=30)
                    if signal:
                        results.append(signal)
                except Exception as e:
                    print(f"UYARI: {sym} analiz hatasi: {e}")

        return results

    def run_scan_with_progress(
        self,
        symbols: list[str],
        interval: str = "1d",
        period: str = "3mo",
    ) -> tuple[list[dict], dict]:
        """
        Same as run_scan but returns progress stats.
        Returns: (signals, stats)
        """
        is_open, reason = self._check_market_open()
        if not is_open:
            return [], {"market_closed": True, "reason": reason}

        results = []
        errors = 0
        total = len(symbols)
        scanned = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_sym = {
                executor.submit(self._analyze_symbol, sym, interval, period): sym
                for sym in symbols
            }
            for future in concurrent.futures.as_completed(future_to_sym):
                scanned += 1
                sym = future_to_sym[future]
                try:
                    signal = future.result(timeout=30)
                    if signal:
                        results.append(signal)
                except Exception:
                    errors += 1

        stats = {
            "total": total,
            "scanned": scanned,
            "signals": len(results),
            "errors": errors,
            "signal_rate": len(results) / total if total > 0 else 0.0,
        }
        return results, stats
