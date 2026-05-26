"""
dynamic_symbol_rotator.py — Dinamik Sembol Rotasyonu (K244)

Sürekli olarak tum sembollerin skorunu izler.
Mevcut sembolun skoru duserse (manipülasyon veya kotu performans)
en yüksek skorlu alternatife otomatik gecis yapar.

Integration: GoldMiningOrchestrator ve SignalEngine ile birlikte calisir.
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
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import threading

import pandas as pd

from data.feed_aggregator import FeedAggregator
from backtest.indicators import apply_all
from backtest.signals import combined_signal
from execution.manipulation_fallback import ManipulationFallbackRouter, FallbackResult


@dataclass
class SymbolScore:
    symbol: str
    score: float
    market: str = "bist"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    regime: str = "NEUTRAL"
    atr: float = 0.0
    volume_z: float = 0.0


class DynamicSymbolRotator:
    """
    Dinamik sembol rotasyonu motoru.

    Usage:
        rotator = DynamicSymbolRotator(bist_universe=BIST_UNIVERSE)
        current = rotator.select_best_symbol()
        rotator.update_scores()  # Periyodik guncelleme
        if rotator.should_rotate(current_symbol):
            new_sym = rotator.get_rotation_target(current_symbol)
    """

    def __init__(
        self,
        bist_universe: List[str] | None = None,
        feed: Optional[FeedAggregator] = None,
        fallback_router: Optional[ManipulationFallbackRouter] = None,
        signal_threshold: float = 70.0,
        rotation_threshold: float = 15.0,  # Skor farki en az bu kadar olmali
        cooldown_minutes: int = 30,
        scan_interval_minutes: int = 15,
        max_positions: int = 3,
        enable_auto_rotate: bool = True,
    ):
        self.bist_universe = bist_universe or []
        self.feed = feed or FeedAggregator()
        self.fallback_router = fallback_router or ManipulationFallbackRouter()
        self.signal_threshold = signal_threshold
        self.rotation_threshold = rotation_threshold
        self.cooldown = timedelta(minutes=cooldown_minutes)
        self.scan_interval = timedelta(minutes=scan_interval_minutes)
        self.max_positions = max_positions
        self.enable_auto_rotate = enable_auto_rotate

        # Sembol skorlari
        self._scores: Dict[str, SymbolScore] = {}
        self._scores_lock = threading.RLock()

        # Rotasyon tarihcesi
        self._rotation_history: List[Dict] = []

        # Son guncelleme
        self._last_scan: Optional[datetime] = None

        # Aktif pozisyonlar (symbol -> entry info)
        self._active_positions: Dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Skor hesaplama
    # ------------------------------------------------------------------
    def _compute_score(self, symbol: str, interval: str = "1d", period: str = "1mo") -> Optional[SymbolScore]:
        """Tek sembol icin kapsamli skor hesaplar."""
        try:
            df = self.feed.fetch(symbol, interval=interval, period=period)
            if len(df) < 50:
                return None

            df = apply_all(df)
            df = combined_signal(df)
            last = df.iloc[-1]

            score = last.get("Signal_Score", 0)
            signal = last.get("Signal", 0)
            if score < self.signal_threshold or signal < 2:
                return None

            # Fallback kontrolu: manipule mi?
            fb = self.fallback_router.fallback(symbol, self.bist_universe)
            if fb.manipulated:
                score *= 0.5  # Manipule sembolun skorunu dusur

            # ATR bazli volatilite cezasi (cok volatil = daha dusuk skor)
            atr = last.get("ATR", 0)
            close = last["close"]
            atr_pct = atr / close if close > 0 else 0
            if atr_pct > 0.05:
                score *= 0.8

            return SymbolScore(
                symbol=symbol.upper(),
                score=score,
                market="bist",
                timestamp=datetime.now(timezone.utc),
                regime="BULL" if close > last.get("EMA21", close) else "BEAR",
                atr=atr,
                volume_z=last.get("Vol_ZScore", 0),
            )
        except Exception:
            return None

    def update_scores(self, symbols: List[str] | None = None) -> Dict[str, SymbolScore]:
        """Tum sembollerin skorlarini gunceller."""
        targets = symbols or self.bist_universe
        now = datetime.now(timezone.utc)

        # Son taramadan beri yeterli zaman gecti mi?
        if self._last_scan and (now - self._last_scan) < self.scan_interval:
            with self._scores_lock:
                return self._scores.copy()

        new_scores = {}
        for sym in targets:
            sc = self._compute_score(sym)
            if sc:
                new_scores[sym.upper()] = sc

        with self._scores_lock:
            self._scores = new_scores
            self._last_scan = now

        return new_scores.copy()

    def get_scores(self) -> Dict[str, SymbolScore]:
        """Mevcut skorlari dondurur."""
        with self._scores_lock:
            return self._scores.copy()

    # ------------------------------------------------------------------
    # Rotasyon karari
    # ------------------------------------------------------------------
    def select_best_symbol(self, exclude: List[str] | None = None) -> Optional[SymbolScore]:
        """En yüksek skorlu sembolu dondurur."""
        with self._scores_lock:
            scores = dict(self._scores)

        if not scores:
            return None

        exclude_set = set((e.upper() for e in (exclude or [])))
        valid = {k: v for k, v in scores.items() if k not in exclude_set}

        if not valid:
            return None

        return max(valid.values(), key=lambda s: s.score)

    def should_rotate(self, current_symbol: str) -> Tuple[bool, str]:
        """
        Mevcut sembolden baska bir semole gecis yapilmali mi?
        Returns: (should_rotate, reason)
        """
        current_symbol = current_symbol.upper()

        # Manipülasyon kontrolu
        fb = self.fallback_router.fallback(current_symbol, self.bist_universe)
        if fb.manipulated:
            return True, f"{current_symbol} manipule edilmis"

        # Skor karsilastirmasi
        with self._scores_lock:
            current = self._scores.get(current_symbol)
            if current is None:
                return True, f"{current_symbol} skoru hesaplanamadi"

            best = self.select_best_symbol(exclude=[current_symbol])
            if best is None:
                return False, "Alternatif bulunamadi"

            score_diff = best.score - current.score
            if score_diff >= self.rotation_threshold:
                return True, (
                    f"{best.symbol} ({best.score:.0f}) "
                    f"{current_symbol} ({current.score:.0f})'den "
                    f"{score_diff:.0f} puan daha iyi"
                )

        return False, "Mevcut sembol hala en iyi secenek"

    def get_rotation_target(self, current_symbol: str) -> Optional[FallbackResult]:
        """Rotasyon hedefini dondurur."""
        current_symbol = current_symbol.upper()

        # Once BIST icinde en iyisini bul
        best = self.select_best_symbol(exclude=[current_symbol])
        if best:
            return FallbackResult(
                original_symbol=current_symbol,
                manipulated=False,
                fallback_symbol=best.symbol,
                fallback_market=best.market,
                fallback_score=best.score,
                reason=f"Daha iyi skorlu alternatif: {best.symbol}",
                alternatives_checked=1,
            )

        # BIST'te yoksa diger piyasalara bak
        return self.fallback_router.fallback(current_symbol, self.bist_universe)

    def record_rotation(self, from_symbol: str, to_symbol: str, reason: str):
        """Rotasyon tarihcesine kayit ekle."""
        self._rotation_history.append({
            "from": from_symbol.upper(),
            "to": to_symbol.upper(),
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_rotation_history(self) -> List[dict]:
        return self._rotation_history.copy()

    # ------------------------------------------------------------------
    # Pozisyon entegrasyonu
    # ------------------------------------------------------------------
    def register_position(self, symbol: str, entry_price: float, size: float):
        """Aktif pozisyon kaydet."""
        self._active_positions[symbol.upper()] = {
            "entry_price": entry_price,
            "size": size,
            "entry_time": datetime.now(timezone.utc),
        }

    def unregister_position(self, symbol: str):
        """Pozisyon kapandiginda kaldir."""
        self._active_positions.pop(symbol.upper(), None)

    def get_active_positions(self) -> Dict[str, dict]:
        return self._active_positions.copy()

    def can_open_new_position(self) -> bool:
        return len(self._active_positions) < self.max_positions
