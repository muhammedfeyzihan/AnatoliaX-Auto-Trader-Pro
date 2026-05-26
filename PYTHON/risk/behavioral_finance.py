"""
behavioral_finance.py — Behavioral Finance Circuit Breaker
K149-K154: FOMO, loss aversion, max daily trades, drawdown scaling, overconfidence.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import statistics


@dataclass
class TradeResult:
    pnl: float
    duration_seconds: float
    timestamp: datetime
    symbol: str = ""


class BehavioralFinanceGuard:
    """
    Psikolojik sapmaları önlemek için davranışsal kontrol motoru.
    """

    def __init__(
        self,
        consecutive_losses_limit: int = 3,
        cooldown_minutes: int = 60,
        fomo_price_change_pct: float = 0.02,
        fomo_window_seconds: float = 300.0,
        fomo_volume_spike_threshold: float = 3.0,
        max_daily_trades: int = 20,
        loss_aversion_ratio_threshold: float = 0.5,
        drawdown_scale_levels: Optional[Dict[float, float]] = None,
        overconfidence_win_streak: int = 8,
        overconfidence_window: int = 10,
        overconfidence_size_reduction: float = 0.25,
    ):
        self.consecutive_losses_limit = consecutive_losses_limit
        self.cooldown_minutes = cooldown_minutes
        self.fomo_price_change_pct = fomo_price_change_pct
        self.fomo_window_seconds = fomo_window_seconds
        self.fomo_volume_spike_threshold = fomo_volume_spike_threshold
        self.max_daily_trades = max_daily_trades
        self.loss_aversion_ratio_threshold = loss_aversion_ratio_threshold
        self.drawdown_scale_levels = drawdown_scale_levels or {
            0.0: 1.0,   # DD < 5%
            0.05: 0.5,  # 5% <= DD < 10%
            0.10: 0.25, # DD >= 10%
        }
        self.overconfidence_win_streak = overconfidence_win_streak
        self.overconfidence_window = overconfidence_window
        self.overconfidence_size_reduction = overconfidence_size_reduction

        self._trades: List[TradeResult] = []
        self._cooldown_until: Optional[datetime] = None
        self._daily_trade_count: Dict[str, int] = {}

    # ── Trade Güncelleme ─────────────────────────────────

    def update_trade(self, trade: TradeResult) -> None:
        """Bir işlem sonucunu kaydet."""
        self._trades.append(trade)
        date_key = trade.timestamp.strftime("%Y-%m-%d")
        self._daily_trade_count[date_key] = self._daily_trade_count.get(date_key, 0) + 1

    def _today_key(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # ── 3-Zarar Cooldown (K149) ──────────────────────────

    def _consecutive_losses(self) -> int:
        """En son üst üste zarar sayısı."""
        count = 0
        for t in reversed(self._trades):
            if t.pnl < 0:
                count += 1
            else:
                break
        return count

    def _check_consecutive_losses(self) -> Optional[str]:
        if self._consecutive_losses() >= self.consecutive_losses_limit:
            if self._cooldown_until is None or datetime.now(timezone.utc) >= self._cooldown_until:
                self._cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=self.cooldown_minutes)
            return f"Consecutive losses >= {self.consecutive_losses_limit}. Cooldown until {self._cooldown_until.isoformat()}"
        self._cooldown_until = None
        return None

    # ── FOMO Tespiti (K150) ──────────────────────────────

    def check_fomo(self, recent_prices: List[float], recent_volumes: List[float]) -> dict:
        """
        Son N fiyat/hacim verisinde FOMO koşulu:
        - Fiyat değişimi > %2
        - Hacim ortalamasının > 3x üstünde
        """
        if len(recent_prices) < 2 or len(recent_volumes) < 2:
            return {"fomo": False, "reduction": 1.0, "reason": "Insufficient data"}

        price_change = (recent_prices[-1] - recent_prices[0]) / recent_prices[0] if recent_prices[0] != 0 else 0
        avg_vol = statistics.mean(recent_volumes[:-1]) if len(recent_volumes) > 1 else recent_volumes[0]
        vol_spike = recent_volumes[-1] / (avg_vol + 1e-8)

        fomo = price_change >= self.fomo_price_change_pct and vol_spike >= self.fomo_volume_spike_threshold
        reduction = 0.5 if fomo else 1.0
        return {
            "fomo": fomo,
            "reduction": reduction,
            "price_change": round(price_change, 4),
            "vol_spike": round(vol_spike, 2),
            "reason": "FOMO detected: price spike + volume spike" if fomo else "No FOMO",
        }

    # ── Kayıp Kaçınma (K151) ─────────────────────────────

    def check_loss_aversion(self) -> dict:
        """
        Ortalama kazançlı işlem süresi / ortalama zararlı işlem süresi.
        Oran < 0.5 → zararlı işlemler çok uzun tutuluyor.
        """
        wins = [t.duration_seconds for t in self._trades if t.pnl > 0]
        losses = [t.duration_seconds for t in self._trades if t.pnl < 0]
        if not wins or not losses:
            return {"ratio": None, "alert": False, "reason": "Need both wins and losses"}
        avg_win_dur = statistics.mean(wins)
        avg_loss_dur = statistics.mean(losses)
        ratio = avg_win_dur / (avg_loss_dur + 1e-8)
        alert = ratio < self.loss_aversion_ratio_threshold
        return {
            "ratio": round(ratio, 4),
            "alert": alert,
            "reason": f"Loss aversion alert: win/loss duration ratio {ratio:.2f} < {self.loss_aversion_ratio_threshold}" if alert else f"Ratio OK: {ratio:.2f}",
        }

    # ── Günlük Max İşlem (K152) ──────────────────────────

    def _check_daily_trade_limit(self) -> Optional[str]:
        count = self._daily_trade_count.get(self._today_key(), 0)
        if count >= self.max_daily_trades:
            return f"Daily trade limit reached: {count}/{self.max_daily_trades}"
        return None

    # ── Drawdown Ölçekleme (K153) ──────────────────────────

    def calculate_drawdown_scale(self, peak_equity: float, current_equity: float) -> dict:
        """
        Drawdown bazlı pozisyon ölçekleme:
        DD < %5 → 1.0x
        %5-10 → 0.5x
        >%10 → 0.25x
        """
        if peak_equity <= 0:
            return {"scale": 1.0, "drawdown": 0.0, "reason": "Invalid peak"}
        dd = (peak_equity - current_equity) / peak_equity
        thresholds = sorted(self.drawdown_scale_levels.keys())
        if dd < thresholds[0]:
            scale = 1.0
        else:
            # Find the interval [t_i, t_{i+1}) that dd falls into
            scale = self.drawdown_scale_levels[thresholds[-1]]
            for i in range(len(thresholds) - 1):
                if thresholds[i] <= dd < thresholds[i + 1]:
                    scale = self.drawdown_scale_levels[thresholds[i]]
                    break
            # If dd is exactly at a boundary, prefer the lower scale
            if dd >= thresholds[-1]:
                scale = self.drawdown_scale_levels[thresholds[-1]]
        return {
            "scale": scale,
            "drawdown": round(dd, 4),
            "reason": f"DD={dd*100:.2f}% → scale={scale}",
        }

    # ── Overconfidence (K154) ────────────────────────────

    def check_overconfidence(self) -> dict:
        """
        Son N işlemde M kazanç → bir sonraki işlem %25 azalt.
        """
        recent = self._trades[-self.overconfidence_window:] if len(self._trades) >= self.overconfidence_window else self._trades
        if len(recent) < self.overconfidence_window:
            return {"alert": False, "reduction": 1.0, "reason": "Insufficient history"}
        wins = sum(1 for t in recent if t.pnl > 0)
        alert = wins >= self.overconfidence_win_streak
        reduction = 1.0 - self.overconfidence_size_reduction if alert else 1.0
        return {
            "alert": alert,
            "reduction": round(reduction, 2),
            "wins": wins,
            "reason": f"Overconfidence: {wins}/{self.overconfidence_window} wins → size ×{reduction}" if alert else f"Confidence OK: {wins}/{self.overconfidence_window}",
        }

    # ── Ana Kontrol (can_trade) ──────────────────────────

    def can_trade(self, signal: dict) -> tuple[bool, str, dict]:
        """
        Sinyal öncesi davranışsal kontrol.
        Returns: (allowed, reason, meta)
        """
        meta = {}

        # Cooldown check
        if self._cooldown_until and datetime.now(timezone.utc) < self._cooldown_until:
            return False, f"Cooldown active until {self._cooldown_until.isoformat()}", meta

        # Consecutive losses
        reason = self._check_consecutive_losses()
        if reason:
            meta["consecutive_losses"] = self._consecutive_losses()
            return False, reason, meta

        # Daily trade limit
        reason = self._check_daily_trade_limit()
        if reason:
            meta["daily_trades"] = self._daily_trade_count.get(self._today_key(), 0)
            return False, reason, meta

        # Overconfidence
        oc = self.check_overconfidence()
        meta["overconfidence"] = oc

        # Loss aversion
        la = self.check_loss_aversion()
        meta["loss_aversion"] = la

        return True, "OK", meta

    def get_behavioral_score(self) -> float:
        """
        0-100 arası davranışsal skor.
        100 = mükemmel, 0 = çok riskli davranış.
        """
        score = 100.0
        # Consecutive losses penalty
        cl = self._consecutive_losses()
        if cl >= 2:
            score -= cl * 15
        # Daily trade proximity
        dt = self._daily_trade_count.get(self._today_key(), 0)
        if dt > self.max_daily_trades * 0.8:
            score -= 10
        # Loss aversion
        la = self.check_loss_aversion()
        if la.get("alert"):
            score -= 15
        # Overconfidence
        oc = self.check_overconfidence()
        if oc.get("alert"):
            score -= 10
        return max(0.0, score)

    def reset_daily(self) -> None:
        """Gün sonu sıfırla."""
        self._daily_trade_count.clear()
        self._cooldown_until = None
