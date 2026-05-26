"""
position_sizing.py — Advanced Position Sizing Engine
K193-K196: Fractional Kelly, Half-Kelly, Optimal f, Volatility Targeting.
"""

import math
import statistics
from typing import Literal, List


class PositionSizer:
    """
    Profesyonel pozisyon ölçekleme modelleri.
    """

    def __init__(self, max_risk_per_trade_pct: float = 0.02):
        self.max_risk_per_trade_pct = max_risk_per_trade_pct

    # ── Fractional Kelly (K193) ──────────────────────────

    def kelly(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        fraction: float = 0.25,
    ) -> float:
        """
        Fractional Kelly Criterion.
        f* = (bp - q) / b  where b = avg_win/avg_loss, p = win_rate, q = 1-p
        Returns: fraction of equity to risk.
        """
        if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
            return 0.0
        b = avg_win / avg_loss
        q = 1.0 - win_rate
        f_star = (b * win_rate - q) / (b + 1e-12)
        if f_star <= 0:
            return 0.0
        return f_star * fraction

    def half_kelly(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
    ) -> float:
        """Half-Kelly: daha konservatif."""
        return self.kelly(win_rate, avg_win, avg_loss, fraction=0.5)

    # ── Optimal f (Ralph Vince) (K194) ─────────────────────

    def optimal_f(self, returns_history: List[float], steps: int = 50) -> float:
        """
        Optimal f: geometrik ortalama maksimize eden f değeri.
        returns_history: per-trade returns as decimal (e.g., 0.03 for 3%)
        """
        if not returns_history:
            return 0.0
        worst_loss = min(returns_history)
        if worst_loss >= 0:
            return 0.0

        best_f = 0.0
        best_geo_mean = -float("inf")
        abs_worst = abs(worst_loss)

        for i in range(1, steps + 1):
            f = i / steps  # 0.02 to 1.0
            hpr = []
            for ret in returns_history:
                # Terminal wealth relative
                if ret >= 0:
                    twr = 1.0 + f * (ret / abs_worst)
                else:
                    twr = 1.0 - f * (abs(ret) / abs_worst)
                hpr.append(twr)
            geo_mean = math.exp(sum(math.log(max(h, 1e-12)) for h in hpr) / len(hpr))
            if geo_mean > best_geo_mean:
                best_geo_mean = geo_mean
                best_f = f

        return best_f

    # ── Volatility Targeting (K195) ──────────────────────

    def volatility_target(
        self,
        base_size: float,
        realized_vol_20d: float,
        target_vol: float = 0.10,
    ) -> float:
        """
        Hedef yıllık volatiliteye göre pozisyon ölçekleme.
        realized_vol_20d: 20-günlük annualized volatilite (decimal)
        target_vol: hedef annualized volatilite (default %10)
        """
        if realized_vol_20d <= 0:
            return base_size
        scale = target_vol / realized_vol_20d
        return base_size * scale

    # ── Unified Sizing API ─────────────────────────────────

    def size(
        self,
        equity: float,
        price: float,
        method: Literal["fractional_kelly", "half_kelly", "optimal_f", "volatility_target", "fixed"],
        **kwargs,
    ) -> int:
        """
        Pozisyon büyüklüğünü hesapla (lot adedi, min 1).
        """
        risk_fraction = 0.0

        if method == "fractional_kelly":
            risk_fraction = self.kelly(
                kwargs.get("win_rate", 0.5),
                kwargs.get("avg_win", 1.0),
                kwargs.get("avg_loss", 1.0),
                kwargs.get("fraction", 0.25),
            )
        elif method == "half_kelly":
            risk_fraction = self.half_kelly(
                kwargs.get("win_rate", 0.5),
                kwargs.get("avg_win", 1.0),
                kwargs.get("avg_loss", 1.0),
            )
        elif method == "optimal_f":
            risk_fraction = self.optimal_f(kwargs.get("returns_history", []))
        elif method == "volatility_target":
            base_size = kwargs.get("base_size", 1.0)
            realized_vol = kwargs.get("realized_vol_20d", 0.10)
            target_vol = kwargs.get("target_vol", 0.10)
            scaled = self.volatility_target(base_size, realized_vol, target_vol)
            notional = scaled * price
            max_notional = equity * self.max_risk_per_trade_pct
            notional = min(notional, max_notional)
            return max(1, int(notional / price)) if price > 0 else 0
        elif method == "fixed":
            risk_fraction = kwargs.get("risk_fraction", 0.02)
        else:
            risk_fraction = self.max_risk_per_trade_pct

        # Cap at max risk per trade
        if price <= 0:
            return 0
        risk_fraction = min(risk_fraction, self.max_risk_per_trade_pct)
        notional = equity * risk_fraction
        qty = int(notional / price)
        return max(1, qty)
