"""
manipulation_fallback.py — Manipülasyon Fallback Router (K243)

Manipülasyon tespit edildiginde otomatik alternatif varliklara gecis.
Öncelik: Ayni borsa farkli hisse -> Kripto -> Forex.

Integration: SignalEngine._check_manipulation() sonrası calisir.
"""

import os
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
from dataclasses import dataclass
import pandas as pd

from data.feed_aggregator import FeedAggregator
from backtest.indicators import apply_all
from backtest.signals import combined_signal
from manipulation.multi_tf_detector import MultiTFManipDetector


@dataclass
class FallbackResult:
    original_symbol: str
    manipulated: bool
    fallback_symbol: Optional[str] = None
    fallback_market: str = "bist"  # bist | crypto | forex
    fallback_score: float = 0.0
    reason: str = ""
    alternatives_checked: int = 0


class ManipulationFallbackRouter:
    """
    Manipülasyon tespiti sonrasi otomatik gecis motoru.

    Usage:
        router = ManipulationFallbackRouter()
        result = router.fallback("THYAO")
        if result.fallback_symbol:
            print(f"THYAO manipule -> {result.fallback_symbol}")
    """

    def __init__(
        self,
        manip_detector: Optional[MultiTFManipDetector] = None,
        feed: Optional[FeedAggregator] = None,
        signal_threshold: float = 70.0,
        blacklist_ttl_minutes: int = 60,
        max_alternatives: int = 10,
        enable_crypto: bool = True,
        enable_forex: bool = False,
        crypto_symbols: List[str] | None = None,
        forex_symbols: List[str] | None = None,
    ):
        self.manip_detector = manip_detector or MultiTFManipDetector()
        self.feed = feed or FeedAggregator()
        self.signal_threshold = signal_threshold
        self.blacklist_ttl = timedelta(minutes=blacklist_ttl_minutes)
        self.max_alternatives = max_alternatives
        self.enable_crypto = enable_crypto
        self.enable_forex = enable_forex

        # Varsayilan kripto ve forex sembolleri
        self.crypto_symbols = crypto_symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT"]
        self.forex_symbols = forex_symbols or ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "XAUUSD=X"]

        # Manipule sembol kara listesi: symbol -> expiry datetime
        self._blacklist: Dict[str, datetime] = {}

    # ------------------------------------------------------------------
    # Blacklist yonetimi
    # ------------------------------------------------------------------
    def _is_blacklisted(self, symbol: str) -> bool:
        expiry = self._blacklist.get(symbol.upper())
        if expiry is None:
            return False
        if datetime.now(timezone.utc) > expiry:
            self._blacklist.pop(symbol.upper(), None)
            return False
        return True

    def blacklist_symbol(self, symbol: str, ttl_minutes: int | None = None):
        """Bir sembolu kara listeye al."""
        ttl = timedelta(minutes=ttl_minutes or int(self.blacklist_ttl.total_seconds() / 60))
        self._blacklist[symbol.upper()] = datetime.now(timezone.utc) + ttl

    def get_blacklist(self) -> Dict[str, datetime]:
        """Kara listedeki sembolleri dondur."""
        now = datetime.now(timezone.utc)
        expired = [s for s, e in self._blacklist.items() if now > e]
        for s in expired:
            self._blacklist.pop(s, None)
        return self._blacklist.copy()

    # ------------------------------------------------------------------
    # Sembol analizi
    # ------------------------------------------------------------------
    def _analyze_symbol(self, symbol: str, interval: str = "1d", period: str = "1mo") -> Optional[dict]:
        """Tek sembol icin skor dondurur."""
        try:
            df = self.feed.fetch(symbol, interval=interval, period=period)
            if len(df) < 30:
                return None
            df = apply_all(df)
            df = combined_signal(df)
            last = df.iloc[-1]
            score = last.get("Signal_Score", 0)
            signal = last.get("Signal", 0)
            if score < self.signal_threshold or signal < 2:
                return None
            return {
                "symbol": symbol,
                "score": score,
                "close": last["close"],
                "market": "bist",
            }
        except Exception:
            return None

    def _check_manipulation(self, symbol: str) -> bool:
        """Coklu zaman diliminde manipülasyon kontrolu."""
        try:
            bars = {}
            for interval, period in [("15m", "5d"), ("1h", "15d"), ("1d", "3mo")]:
                try:
                    df = self.feed.fetch(symbol, interval=interval, period=period)
                    if df is not None and len(df) >= 30:
                        bars[interval] = df
                except Exception:
                    continue
            if not bars:
                return False
            result = self.manip_detector.scan(symbol, bars=bars)
            return result.is_manipulated
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Fallback piyasa tarama
    # ------------------------------------------------------------------
    def _scan_bist_alternatives(self, exclude_symbol: str, bist_universe: List[str]) -> Optional[dict]:
        """BIST'te manipülasyon disi en iyi sembolu bul."""
        candidates = []
        checked = 0

        for sym in bist_universe:
            if sym.upper() == exclude_symbol.upper():
                continue
            if self._is_blacklisted(sym):
                continue
            checked += 1
            if checked > self.max_alternatives:
                break

            info = self._analyze_symbol(sym)
            if info:
                candidates.append(info)

        if not candidates:
            return None

        best = max(candidates, key=lambda x: x["score"])
        return best

    def _scan_crypto_alternatives(self) -> Optional[dict]:
        """Kripto piyasasinda en iyi sembolu bul."""
        if not self.enable_crypto:
            return None

        from adapters.exchange_adapter import ExchangeAdapter
        adapter = ExchangeAdapter("binance")

        candidates = []
        for sym in self.crypto_symbols:
            try:
                ticker = adapter.get_ticker(sym)
                if ticker is None:
                    continue
                # Basit momentum skoru: 24h degisim
                change_24h = ticker.change_percent if hasattr(ticker, "change_percent") else 0.0
                score = 50 + abs(change_24h) * 2  # Basit skor
                if score >= self.signal_threshold:
                    candidates.append({
                        "symbol": sym,
                        "score": score,
                        "close": ticker.last,
                        "market": "crypto",
                    })
            except Exception:
                continue

        if not candidates:
            return None
        return max(candidates, key=lambda x: x["score"])

    def _scan_forex_alternatives(self) -> Optional[dict]:
        """Forex piyasasinda en iyi sembolu bul."""
        if not self.enable_forex:
            return None

        from data.yahoo_fetcher import YahooFetcher
        fetcher = YahooFetcher()

        candidates = []
        for sym in self.forex_symbols:
            try:
                df = fetcher.fetch(sym, period="1mo", interval="1d")
                if df is None or len(df) < 10:
                    continue
                last = df.iloc[-1]
                change = (last["close"] - df.iloc[0]["close"]) / df.iloc[0]["close"] * 100
                score = 50 + abs(change) * 5
                if score >= self.signal_threshold:
                    candidates.append({
                        "symbol": sym,
                        "score": score,
                        "close": last["close"],
                        "market": "forex",
                    })
            except Exception:
                continue

        if not candidates:
            return None
        return max(candidates, key=lambda x: x["score"])

    # ------------------------------------------------------------------
    # Ana fallback API
    # ------------------------------------------------------------------
    def fallback(
        self,
        symbol: str,
        bist_universe: List[str] | None = None,
    ) -> FallbackResult:
        """
        Manipülasyon tespiti sonrasi en iyi alternatifi bul.

        Returns FallbackResult with fallback_symbol set if found.
        """
        symbol = symbol.upper()

        # Önce kendi manipülasyon kontrolu
        is_manip = self._check_manipulation(symbol)
        was_blacklisted = self._is_blacklisted(symbol)

        if is_manip:
            self.blacklist_symbol(symbol)

        # Eger kara listedeyse veya manipule edilmisse fallback ara
        if not is_manip and not was_blacklisted:
            return FallbackResult(
                original_symbol=symbol,
                manipulated=False,
                reason="Sembol temiz, gecise gerek yok",
                alternatives_checked=0,
            )

        # 1. Öncelik: Ayni borsa (BIST) farkli hisse
        if bist_universe:
            alt = self._scan_bist_alternatives(symbol, bist_universe)
            if alt:
                return FallbackResult(
                    original_symbol=symbol,
                    manipulated=is_manip or was_blacklisted,
                    fallback_symbol=alt["symbol"],
                    fallback_market="bist",
                    fallback_score=alt["score"],
                    reason="BIST icinde manipülasyonsuz alternatif bulundu",
                    alternatives_checked=1,
                )

        # 2. Öncelik: Kripto
        alt = self._scan_crypto_alternatives()
        if alt:
            return FallbackResult(
                original_symbol=symbol,
                manipulated=is_manip or was_blacklisted,
                fallback_symbol=alt["symbol"],
                fallback_market="crypto",
                fallback_score=alt["score"],
                reason="Kripto piyasasina gecis yapildi",
                alternatives_checked=2,
            )

        # 3. Öncelik: Forex
        alt = self._scan_forex_alternatives()
        if alt:
            return FallbackResult(
                original_symbol=symbol,
                manipulated=is_manip or was_blacklisted,
                fallback_symbol=alt["symbol"],
                fallback_market="forex",
                fallback_score=alt["score"],
                reason="Forex piyasasina gecis yapildi",
                alternatives_checked=3,
            )

        # Hicbir alternatif bulunamadi
        return FallbackResult(
            original_symbol=symbol,
            manipulated=is_manip or was_blacklisted,
            fallback_symbol=None,
            fallback_market="none",
            fallback_score=0.0,
            reason="Manipülasyon tespit edildi ama hicbir alternatif bulunamadi",
            alternatives_checked=3,
        )

    def fallback_multi(
        self,
        symbols: List[str],
        bist_universe: List[str] | None = None,
    ) -> Dict[str, FallbackResult]:
        """Birden fazla sembol icin fallback kontrolu."""
        results = {}
        for sym in symbols:
            results[sym.upper()] = self.fallback(sym, bist_universe)
        return results
