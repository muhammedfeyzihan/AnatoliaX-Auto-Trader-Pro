"""
nautilus_adapter.py — Nautilus Trader Referans Adaptörü (Opsiyonel)

Ana mimariyi bozmadan, Nautilus Trader'in event-driven engine,
precision ve multi-venue ozelliklerinden yararlanir.

Kullanim:
    from adapters.nautilus_adapter import NautilusAdapter
    adapter = NautilusAdapter()
    adapter.register_symbol("THYAO")
    adapter.place_market_order("THYAO", "BUY", 100)

Gereksinimler (opsiyonel):
    pip install nautilus_trader

Not: Nautilus kurulu degilse graceful fallback — mevcut AnatoliaX motoru calisir.
"""
import os
import sys
import time
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

from typing import Optional

# Nautilus opsiyonel — yoksa ImportError yakalanir
_NAUTILUS_AVAILABLE = False
try:
    from nautilus_trader.model.data import Bar, BarType
    from nautilus_trader.model.identifiers import Venue
    from nautilus_trader.model.instruments import Equity
    from nautilus_trader.model.objects import Quantity, Money
    _NAUTILUS_AVAILABLE = True
except ImportError:
    pass


class NautilusAdapter:
    """
    Nautilus Trader entegrasyonu (opsiyonel).
    Mevcut AnatoliaX motorunu bozmaz — adaptör pattern.
    """

    def __init__(self, venue: str = "BIST"):
        self.venue = venue
        self._available = _NAUTILUS_AVAILABLE
        self._symbols: set[str] = set()

    def is_available(self) -> bool:
        return self._available

    def register_symbol(self, symbol: str) -> bool:
        """Sembolu Nautilus'a kaydet (mock)."""
        if not self._available:
            return False
        self._symbols.add(symbol)
        return True

    def place_market_order(self, symbol: str, side: str, size: int) -> dict:
        """
        Piyasa emri gonder.
        Nautilus yoksa veya canli mod aktif degilse PaperBroker'a fallback.
        """
        live_mode = os.getenv("NAUTILUS_LIVE", "false").lower() == "true"
        if not self._available or not live_mode:
            return self._fallback_order(symbol, side, size)

        # Nautilus canli entegrasyonu — gercek emir yolu
        # Not: Tam implementasyon icin Nautilus TradingNode, Venue ve Instrument
        # tanimlari gereklidir. Bu stub, canli modda PaperBroker'a yonlendirir.
        return self._fallback_order(symbol, side, size)

    def place_limit_order(self, symbol: str, side: str, size: int, price: float) -> dict:
        """Limit emir (opsiyonel)."""
        live_mode = os.getenv("NAUTILUS_LIVE", "false").lower() == "true"
        if not self._available or not live_mode:
            return self._fallback_order(symbol, side, size, price=price)
        return self._fallback_order(symbol, side, size, price=price)

    def get_instrument(self, symbol: str) -> Optional[dict]:
        """Enstruman bilgisi."""
        if not self._available:
            return {"symbol": symbol, "venue": self.venue, "provider": "fallback"}
        return {
            "symbol": symbol,
            "venue": self.venue,
            "provider": "nautilus",
            "precision": 2,
            "min_size": 1,
        }

    # ------------------------------------------------------------------
    # Deterministic replay engine
    # ------------------------------------------------------------------
    def replay_start(self, ticks: list[dict], initial_state: Optional[dict] = None) -> dict:
        """
        Start a deterministic replay session.
        ticks: list of {"timestamp": str, "price": float, "volume": float, "side": str}
        initial_state: optional starting portfolio state
        Returns replay session metadata.
        """
        self._replay_log: list[dict] = []
        self._replay_state = initial_state or {"cash": 100_000.0, "positions": {}, "trades": 0}
        self._replay_ticks = list(ticks)
        self._replay_idx = 0
        return {
            "session_id": f"replay_{id(self)}_{int(time.time())}",
            "tick_count": len(ticks),
            "initial_state": self._replay_state.copy(),
            "provider": "nautilus_replay",
        }

    def replay_step(self) -> Optional[dict]:
        """Process one tick in the replay. Returns fill event or None."""
        if not hasattr(self, "_replay_ticks") or self._replay_idx >= len(self._replay_ticks):
            return None
        tick = self._replay_ticks[self._replay_idx]
        self._replay_idx += 1
        event = {
            "idx": self._replay_idx,
            "timestamp": tick.get("timestamp"),
            "price": tick.get("price"),
            "volume": tick.get("volume"),
            "state_before": self._replay_state.copy(),
        }
        # Update state deterministically
        price = tick.get("price", 0.0)
        if price > 0:
            for sym, pos in self._replay_state.get("positions", {}).items():
                pos["mkt_price"] = price
                pos["unrealized"] = (price - pos.get("entry", price)) * pos.get("qty", 0)
        event["state_after"] = self._replay_state.copy()
        self._replay_log.append(event)
        return event

    def replay_validate(self, expected_state: dict, tolerance: float = 1e-9) -> dict:
        """Validate replay state against expected state."""
        mismatches = []
        for key, expected in expected_state.items():
            actual = self._replay_state.get(key)
            if isinstance(expected, float) and isinstance(actual, float):
                if abs(expected - actual) > tolerance:
                    mismatches.append(f"{key}: expected {expected}, got {actual}")
            elif expected != actual:
                mismatches.append(f"{key}: expected {expected}, got {actual}")
        return {
            "valid": len(mismatches) == 0,
            "mismatches": mismatches,
            "final_state": self._replay_state.copy(),
            "ticks_processed": self._replay_idx,
        }

    def state_checksum(self) -> str:
        """Return a deterministic checksum of current replay state."""
        import hashlib, json
        state = getattr(self, "_replay_state", {})
        payload = json.dumps(state, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def get_replay_log(self) -> list[dict]:
        return list(getattr(self, "_replay_log", []))

    def _fallback_order(self, symbol: str, side: str, size: int, price: Optional[float] = None) -> dict:
        """Nautilus yoksa mevcut PaperBroker'a yonlendir."""
        try:
            from paper_trading.paper_broker import PaperBroker
            broker = PaperBroker()
            trade = broker.place_order(
                symbol=symbol,
                side=side,
                size=size,
                price=price or 0.0,
            )
            if trade:
                return {
                    "order_id": str(trade.id),
                    "symbol": symbol,
                    "side": side,
                    "size": size,
                    "price": price,
                    "status": "FILLED",
                    "provider": "paper_fallback",
                }
        except Exception:
            pass
        return {
            "order_id": None,
            "symbol": symbol,
            "side": side,
            "size": size,
            "price": price,
            "status": "ERROR",
            "provider": "none",
            "error": "Nautilus ve PaperBroker calismiyor.",
        }


if __name__ == "__main__":
    adapter = NautilusAdapter()
    print("Nautilus kurulu mu:", adapter.is_available())
    r = adapter.place_market_order("THYAO", "BUY", 100)
    print("Emir sonucu:", r)
