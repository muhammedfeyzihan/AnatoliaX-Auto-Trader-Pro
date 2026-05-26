"""
bist_regulations.py — BIST Regulatory Compliance Engine
K142-K148: VBTS, circuit breakers, short selling ban, margin, stopaj, order/trade ratio.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Literal


@dataclass
class VBTSMeasure:
    """BIST VBTS (Volatility Based Temporary Measure) kaydı."""
    symbol: str
    tier: int  # 1-5
    description: str
    start_date: datetime
    end_date: Optional[datetime] = None


@dataclass
class CircuitBreakerState:
    """Devre kesici durumu."""
    triggered: bool = False
    level: float = 0.0  # -0.05, -0.07 for index; +/-0.05, 0.075, 0.10 for stock
    duration_minutes: int = 0
    reason: str = ""
    triggered_at: Optional[datetime] = None


class BISTRegulatoryChecker:
    """
    BIST resmi regülasyonlarını otomatik kontrol eden motor.
    """

    # BIST spot piyasası için kısa satış tamamen yasak
    SHORT_SELLING_ALLOWED = False

    # Günlük fiyat sınırları (referans fiyata göre ±%20)
    DAILY_PRICE_LIMIT_PCT = 0.20

    # Endeks bazlı devre kesici
    INDEX_CIRCUIT_BREAKER_LEVELS = {
        -0.05: {"duration_minutes": 15, "reason": "BIST100 -%5"},
        -0.07: {"duration_minutes": None, "reason": "BIST100 -%7 (gün sonu)"},
    }

    # Hisse bazlı devre kesici (fiyat aralığına göre tier)
    STOCK_CIRCUIT_BREAKER_TIERS = {
        "low": {"limit": 0.05, "price_max": 10.0},
        "mid": {"limit": 0.075, "price_max": 50.0},
        "high": {"limit": 0.10, "price_max": float("inf")},
    }

    # Kredili işlem teminat oranı minimum %20
    MIN_MARGIN_RATIO = 0.20

    # Emir/işlem oranı minimum 3:1
    MIN_ORDER_TRADE_RATIO = 3.0

    # Temettü stopajı %15
    DIVIDEND_WITHHOLDING_TAX_PCT = 0.15

    def __init__(self, vbts_measures: Optional[List[VBTSMeasure]] = None):
        self.vbts_registry: Dict[str, List[VBTSMeasure]] = {}
        self._circuit_states: Dict[str, CircuitBreakerState] = {}
        # Net long positions per symbol (positive = long, negative = short)
        self._positions: Dict[str, float] = {}
        if vbts_measures:
            for m in vbts_measures:
                self.vbts_registry.setdefault(m.symbol, []).append(m)

    # ── Pozisyon Takibi (Short Selling Kontrolü) ──────────

    def update_position(self, symbol: str, side: str, size: float) -> None:
        """İşlem sonrası pozisyonu güncelle."""
        sym = symbol.upper()
        current = self._positions.get(sym, 0.0)
        if side == "BUY":
            self._positions[sym] = current + size
        elif side == "SELL":
            self._positions[sym] = current - size

    def get_position(self, symbol: str) -> float:
        """Sembolün mevcut net pozisyonunu döner."""
        return self._positions.get(symbol.upper(), 0.0)

    def check_short_selling(self, symbol: str, side: str, size: float) -> dict:
        """
        BIST spot piyasada açığa satış yasak.
        SELL emri mevcut pozisyondan büyükse short selling oluşur.
        """
        if side != "SELL":
            return {"allowed": True, "reason": "Not a sell order"}
        current = self.get_position(symbol)
        if current <= 0:
            return {"allowed": False, "reason": f"No long position to sell. Current: {current}"}
        if size > current:
            return {
                "allowed": False,
                "reason": f"Sell size {size} exceeds long position {current}. Short selling banned on BIST spot.",
            }
        return {"allowed": True, "reason": "Closing existing long position"}

    # ── VBTS ───────────────────────────────────────────────

    def check_vbts_measures(self, symbol: str) -> List[str]:
        """Sembolün hangi VBTS tedbirlerinde olduğunu döner."""
        measures = self.vbts_registry.get(symbol.upper(), [])
        active = []
        now = datetime.now(timezone.utc)
        for m in measures:
            if now >= m.start_date and (m.end_date is None or now <= m.end_date):
                active.append(f"VBTS Tier {m.tier}: {m.description}")
        return active

    def is_vbts_restricted(self, symbol: str) -> bool:
        """Sembol herhangi bir VBTS tedbirinde mi?"""
        return len(self.check_vbts_measures(symbol)) > 0

    # ── Fiyat Sınırları ──────────────────────────────────

    def check_price_limits(self, current_price: float, reference_price: float) -> dict:
        """Günlük ±%20 fiyat limit kontrolü."""
        if reference_price <= 0:
            return {"valid": False, "reason": "Invalid reference price"}
        lower = reference_price * (1 - self.DAILY_PRICE_LIMIT_PCT)
        upper = reference_price * (1 + self.DAILY_PRICE_LIMIT_PCT)
        valid = lower <= current_price <= upper
        return {
            "valid": valid,
            "lower": round(lower, 4),
            "upper": round(upper, 4),
            "reason": "" if valid else f"Price {current_price} outside ±%20 band [{lower:.4f}, {upper:.4f}]",
        }

    # ── Devre Kesici (Index) ─────────────────────────────

    def check_index_circuit_breaker(
        self,
        index_level: float,
        previous_close: float,
    ) -> CircuitBreakerState:
        """BIST100 endeks bazlı devre kesici kontrolü."""
        if previous_close <= 0:
            return CircuitBreakerState(triggered=False)
        change_pct = (index_level - previous_close) / previous_close
        state = CircuitBreakerState()
        for level_pct, info in sorted(self.INDEX_CIRCUIT_BREAKER_LEVELS.items()):
            if change_pct <= level_pct:
                state = CircuitBreakerState(
                    triggered=True,
                    level=level_pct,
                    duration_minutes=info["duration_minutes"],
                    reason=info["reason"],
                    triggered_at=datetime.now(timezone.utc),
                )
                break
        self._circuit_states["BIST100"] = state
        return state

    # ── Devre Kesici (Stock) ─────────────────────────────

    def _stock_circuit_tier(self, price: float) -> str:
        """Fiyat aralığına göre devre kesici tier'ı."""
        if price <= self.STOCK_CIRCUIT_BREAKER_TIERS["low"]["price_max"]:
            return "low"
        elif price <= self.STOCK_CIRCUIT_BREAKER_TIERS["mid"]["price_max"]:
            return "mid"
        return "high"

    def check_stock_circuit_breaker(
        self,
        symbol: str,
        price: float,
        reference_price: float,
    ) -> CircuitBreakerState:
        """Hisse bazlı devre kesici kontrolü."""
        if reference_price <= 0:
            return CircuitBreakerState(triggered=False)
        change_pct = (price - reference_price) / reference_price
        tier_key = self._stock_circuit_tier(reference_price)
        limit = self.STOCK_CIRCUIT_BREAKER_TIERS[tier_key]["limit"]
        state = CircuitBreakerState()
        if abs(change_pct) >= limit:
            state = CircuitBreakerState(
                triggered=True,
                level=limit if change_pct > 0 else -limit,
                duration_minutes=15,
                reason=f"{symbol} {'+%' if change_pct > 0 else '-%'}{limit*100} ({tier_key} tier)",
                triggered_at=datetime.now(timezone.utc),
            )
        self._circuit_states[symbol.upper()] = state
        return state

    # ── Kısa Satış ───────────────────────────────────────

    def is_short_selling_allowed(self, symbol: str) -> bool:
        """BIST spot piyasada kısa satış her zaman yasak."""
        return False

    # ── Emir/İşlem Oranı ─────────────────────────────────

    def check_order_trade_ratio(self, orders: int, trades: int) -> dict:
        """Emir/işlem oranı >= 3:1 kontrolü."""
        if trades <= 0:
            return {"valid": False, "ratio": float("inf"), "reason": "Zero trades"}
        ratio = orders / trades
        valid = ratio >= self.MIN_ORDER_TRADE_RATIO
        return {
            "valid": valid,
            "ratio": round(ratio, 2),
            "reason": "" if valid else f"Order/trade ratio {ratio:.2f} < {self.MIN_ORDER_TRADE_RATIO}",
        }

    # ── Teminat Oranı ────────────────────────────────────

    def check_margin_requirement(self, position_value: float, cash: float) -> dict:
        """Kredili işlemde minimum %20 teminat kontrolü."""
        if position_value <= 0:
            return {"valid": True, "ratio": float("inf"), "reason": "No position"}
        ratio = cash / position_value
        valid = ratio >= self.MIN_MARGIN_RATIO
        return {
            "valid": valid,
            "ratio": round(ratio, 4),
            "reason": "" if valid else f"Margin ratio {ratio*100:.2f}% < {self.MIN_MARGIN_RATIO*100}%",
        }

    # ── Stopaj ───────────────────────────────────────────

    def calculate_dividend_tax(self, dividend_amount: float) -> dict:
        """Temettü üzerinden %15 stopaj hesaplama."""
        tax = dividend_amount * self.DIVIDEND_WITHHOLDING_TAX_PCT
        net = dividend_amount - tax
        return {
            "gross": dividend_amount,
            "tax": tax,
            "net": net,
            "rate": self.DIVIDEND_WITHHOLDING_TAX_PCT,
        }

    # ── Toplu Kontrol ────────────────────────────────────

    def validate_trade(
        self,
        symbol: str,
        price: float,
        reference_price: float,
        index_level: float,
        index_previous_close: float,
        orders_today: int,
        trades_today: int,
        position_value: float,
        cash: float,
        side: Literal["BUY", "SELL"],
        size: float = 0.0,
    ) -> dict:
        """Bir işlem öncesi tüm BIST regülasyonlarını kontrol et."""
        errors = []

        # VBTS
        vbts = self.check_vbts_measures(symbol)
        if vbts:
            errors.append(f"VBTS active: {vbts}")

        # Price limits
        pl = self.check_price_limits(price, reference_price)
        if not pl["valid"]:
            errors.append(pl["reason"])

        # Index circuit breaker
        idx_cb = self.check_index_circuit_breaker(index_level, index_previous_close)
        if idx_cb.triggered:
            errors.append(f"Index CB: {idx_cb.reason}")

        # Stock circuit breaker
        stock_cb = self.check_stock_circuit_breaker(symbol, price, reference_price)
        if stock_cb.triggered:
            errors.append(f"Stock CB: {stock_cb.reason}")

        # Short selling
        short_check = self.check_short_selling(symbol, side, size)
        if not short_check["allowed"]:
            errors.append(short_check["reason"])

        # Order/trade ratio
        otr = self.check_order_trade_ratio(orders_today, trades_today)
        if not otr["valid"]:
            errors.append(otr["reason"])

        # Margin
        margin = self.check_margin_requirement(position_value, cash)
        if not margin["valid"]:
            errors.append(margin["reason"])

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "vbts": vbts,
            "price_limit": pl,
            "index_cb": idx_cb,
            "stock_cb": stock_cb,
            "order_trade_ratio": otr,
            "margin": margin,
        }
