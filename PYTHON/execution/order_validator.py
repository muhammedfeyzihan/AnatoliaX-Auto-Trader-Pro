"""
order_validator.py — Pydantic tabanli emir validasyonu.
AnatoliaX icin özgün implementasyon.

Kullanim:
    from execution.order_validator import OrderValidator
    validator = OrderValidator()
    result = validator.validate({"symbol": "THYAO", "side": "BUY", "size": 10.0, "price": 100.0, "sl": 95.0, "tp": 110.0})
    # result: {"valid": True, "errors": []}
"""
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

from typing import Literal, Optional


try:
    from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

    PYDANTIC_AVAILABLE = True
except Exception:
    PYDANTIC_AVAILABLE = False
    BaseModel = object


class _OrderSchema(BaseModel):
    """Pydantic emir semasi (Pydantic V2)."""

    max_size: float = 1_000_000.0  # Konfigurasyon uzerinden override edilebilir (size'dan once tanimlanmali)
    symbol: str = Field(..., min_length=3, max_length=20)
    side: Literal["BUY", "SELL"]
    size: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    sl: Optional[float] = Field(None, gt=0)
    tp: Optional[float] = Field(None, gt=0)
    order_type: Literal["MARKET", "LIMIT", "STOP"] = "MARKET"
    time_in_force: Literal["DAY", "GTC", "IOC", "FOK"] = "DAY"

    @field_validator("symbol")
    @classmethod
    def symbol_uppercase(cls, v):
        return v.upper().strip()

    @field_validator("size")
    @classmethod
    def size_within_limit(cls, v, info):
        max_size = info.data.get("max_size", 1_000_000.0)
        if v > max_size:
            raise ValueError(f"Pozisyon boyutu max {max_size} olabilir")
        return v

    @model_validator(mode="after")
    def sl_tp_consistency(self):
        side = self.side
        price = self.price
        sl = self.sl
        tp = self.tp
        if side == "BUY":
            if sl is not None and sl >= price:
                raise ValueError("BUY emirde SL, entry fiyatindan dusuk olmali")
            if tp is not None and tp <= price:
                raise ValueError("BUY emirde TP, entry fiyatindan yuksek olmali")
        elif side == "SELL":
            if sl is not None and sl <= price:
                raise ValueError("SELL emirde SL, entry fiyatindan yuksek olmali")
            if tp is not None and tp >= price:
                raise ValueError("SELL emirde TP, entry fiyatindan dusuk olmali")
        return self


class OrderValidator:
    """
    Emir validasyonu: Pydantic varsa kullanir, yoksa manuel kontrol.
    Entegrasyon: UnifiedExecutionEngine.place_order() ilk satirinda validate.
    """

    def __init__(self, max_size: float = 1_000_000.0):
        self.max_size = max_size

    def validate(self, order: dict) -> dict:
        """
        Emir validasyonu yap.

        Donus: {"valid": bool, "errors": [str, ...]}
        """
        if PYDANTIC_AVAILABLE:
            return self._pydantic_validate(order)
        return self._manual_validate(order)

    def _pydantic_validate(self, order: dict) -> dict:
        try:
            data = dict(order)
            data["max_size"] = self.max_size
            _OrderSchema(**data)
            return {"valid": True, "errors": []}
        except ValidationError as e:
            errors = []
            for err in e.errors():
                field = ".".join(str(x) for x in err.get("loc", []))
                msg = err.get("msg", "Bilinmeyen hata")
                errors.append(f"{field}: {msg}")
            return {"valid": False, "errors": errors}
        except Exception as e:
            return {"valid": False, "errors": [str(e)]}

    def _manual_validate(self, order: dict) -> dict:
        errors = []
        symbol = str(order.get("symbol", "")).strip().upper()
        side = str(order.get("side", "")).upper()
        size = order.get("size")
        price = order.get("price")
        sl = order.get("sl")
        tp = order.get("tp")

        if len(symbol) < 3:
            errors.append("symbol: En az 3 karakter olmali")
        if side not in ("BUY", "SELL"):
            errors.append("side: BUY veya SELL olmali")
        if not isinstance(size, (int, float)) or size <= 0:
            errors.append("size: 0'dan buyuk olmali")
        if size > self.max_size:
            errors.append(f"size: Max {self.max_size} olabilir")
        if not isinstance(price, (int, float)) or price <= 0:
            errors.append("price: 0'dan buyuk olmali")

        if sl is not None:
            if side == "BUY" and sl >= price:
                errors.append("sl: BUY emirde SL, entry fiyatindan dusuk olmali")
            if side == "SELL" and sl <= price:
                errors.append("sl: SELL emirde SL, entry fiyatindan yuksek olmali")
        if tp is not None:
            if side == "BUY" and tp <= price:
                errors.append("tp: BUY emirde TP, entry fiyatindan yuksek olmali")
            if side == "SELL" and tp >= price:
                errors.append("tp: SELL emirde TP, entry fiyatindan dusuk olmali")

        return {"valid": len(errors) == 0, "errors": errors}

    def validate_batch(self, orders: list[dict]) -> list[dict]:
        return [self.validate(o) for o in orders]


if __name__ == "__main__":
    v = OrderValidator()
    print(v.validate({"symbol": "THYAO", "side": "BUY", "size": 10, "price": 100, "sl": 95, "tp": 110}))
    print(v.validate({"symbol": "THYAO", "side": "BUY", "size": 10, "price": 100, "sl": 105, "tp": 110}))
