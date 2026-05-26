"""
auto_validator.py — Otomatik Veri Doğrulama Motoru
Ajan analizlerini canli fiyatlarla otomatik dogrular.
Kural K91: TradingView dogrulamadan analiz = RED
"""
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

import requests
import pandas as pd
from datetime import datetime, timedelta
from data.feed_aggregator import FeedAggregator


class AutoValidator:
    """
    TradingView (birincil) ve diger kaynaklardan anlik fiyat cekerek
    ajan analizlerini otomatik dogrular.

    Kullanim:
        validator = AutoValidator()
        result = validator.validate_symbol("THYAO", expected_price=305.0)
        # result: {"valid": True/False, "deviation_pct": 0.5, "source": "yahoo", ...}
    """

    DEVIATION_LIMIT_PCT = 1.0  # %1 sapma limiti

    def __init__(self):
        self.feed = FeedAggregator()
        self.source = "auto_validator"

    def validate_symbol(
        self,
        symbol: str,
        expected_price: float | None = None,
        expected_sl: float | None = None,
        expected_tp: float | None = None,
    ) -> dict:
        """
        Sembol icin canli fiyat cek ve beklenen degerlerle karsilastir.
        Returns: {"valid": bool, "deviation_pct": float, "live_price": float, "source": str, "reason": str}
        """
        result = {
            "symbol": symbol,
            "valid": False,
            "deviation_pct": 0.0,
            "live_price": 0.0,
            "source": "",
            "reason": "",
            "timestamp": datetime.now(),
        }

        try:
            # Anlik veri cek (1 gunluk, son satir = son fiyat)
            df = self.feed.fetch(symbol, interval="1d", period="5d")
            if df.empty:
                result["reason"] = "Fiyat verisi cekilemedi (tum kaynaklar basarisiz)"
                return result

            last = df.iloc[-1]
            live_price = float(last["close"])
            source = str(last.get("source", "unknown"))

            result["live_price"] = live_price
            result["source"] = source

            # Beklenen fiyat kontrolu
            if expected_price is not None and expected_price > 0:
                deviation = abs(live_price - expected_price) / expected_price * 100
                result["deviation_pct"] = round(deviation, 2)

                if deviation > self.DEVIATION_LIMIT_PCT:
                    result["reason"] = (
                        f"SAPMA: Beklenen {expected_price:.2f} | Gercek {live_price:.2f} "
                        f"| Sapma %{deviation:.2f} (Limit %{self.DEVIATION_LIMIT_PCT})"
                    )
                    return result

            # SL kontrolu
            if expected_sl is not None and expected_sl > 0:
                if live_price <= expected_sl:
                    result["reason"] = f"STOP: Fiyat ({live_price:.2f}) SL ({expected_sl:.2f}) altina dustu"
                    return result

            # TP kontrolu
            if expected_tp is not None and expected_tp > 0:
                if live_price >= expected_tp:
                    result["reason"] = f"TP: Fiyat ({live_price:.2f}) TP ({expected_tp:.2f}) uzerine cikti"
                    return result

            result["valid"] = True
            result["reason"] = f"DOGRULANDI: {symbol} {live_price:.2f} TL ({source}, {datetime.now().strftime('%H:%M')})"

        except Exception as e:
            result["reason"] = f"HATA: Dogrulama sirasinda hata olustu: {e}"

        return result

    def validate_batch(
        self,
        validations: list[dict],
    ) -> list[dict]:
        """
        Birden fazla sembolu ayni anda dogrula.
        validations: [{"symbol": "THYAO", "expected_price": 305.0, ...}, ...]
        Returns: [result_dict, ...]
        """
        results = []
        for v in validations:
            result = self.validate_symbol(
                symbol=v["symbol"],
                expected_price=v.get("expected_price"),
                expected_sl=v.get("expected_sl"),
                expected_tp=v.get("expected_tp"),
            )
            results.append(result)
        return results

    def monitor_open_positions(
        self,
        positions: list[dict],
    ) -> list[dict]:
        """
        Acik pozisyonlari surekli dogrula (SL/TP takibi).
        positions: [{"symbol": "THYAO", "entry": 300, "sl": 290, "tp": 320}, ...]
        Returns: Her pozisyon icin alarm listesi (bos = sorun yok)
        """
        alarms = []
        for pos in positions:
            result = self.validate_symbol(
                symbol=pos["symbol"],
                expected_sl=pos.get("sl"),
                expected_tp=pos.get("tp"),
            )
            if not result["valid"]:
                alarms.append({
                    "symbol": pos["symbol"],
                    "alarm_type": result["reason"].split(":")[0],
                    "live_price": result["live_price"],
                    "message": result["reason"],
                })
        return alarms


if __name__ == "__main__":
    validator = AutoValidator()
    # Tek sembol dogrulama
    result = validator.validate_symbol("THYAO", expected_price=305.0)
    print(f"Dogrulama: {result}")

    # Acik pozisyon takibi
    positions = [
        {"symbol": "THYAO", "entry": 300.0, "sl": 290.0, "tp": 320.0},
        {"symbol": "GARAN", "entry": 45.0, "sl": 43.0, "tp": 50.0},
    ]
    alarms = validator.monitor_open_positions(positions)
    print(f"Alarmlar: {alarms}")
