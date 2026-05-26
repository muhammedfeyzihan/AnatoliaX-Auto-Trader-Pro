"""
arbitrage_detector.py — Cross-Venue Arbitraj ve Cross-Asset Korelasyon Bozulmasi Tespiti
AutoTrader'dan entegre edilmistir.

Kullanim:
    from analytics.arbitrage_detector import ArbitrageDetector
    det = ArbitrageDetector()
    opp = det.check_symbol("THYAO")
    # opp: {"symbol": "THYAO", "deviation_pct": 0.6, "venues": [...]} veya None
"""
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

import numpy as np
import pandas as pd
from typing import Optional
from data.feed_aggregator import FeedAggregator


class ArbitrageDetector:
    """
    Ayni hissenin farkli kaynaklardaki fiyatini karsilastir.
    BIST/USDTRY bazli cross-asset arbitraj tespiti.

    Kural K145: Arbitraj sinyali = bilgi amacli, dogrudan islem yapilmaz.
    """

    def __init__(
        self,
        deviation_threshold_pct: float = 0.5,
        min_volume: Optional[float] = None,
    ):
        self.deviation_threshold = deviation_threshold_pct / 100.0
        self.min_volume = min_volume
        self.feed = FeedAggregator()

    def check_symbol(self, symbol: str) -> Optional[dict]:
        """
        Tek hisse icin tum kaynaklardan fiyat cek ve sapmayi kontrol et.

        Donus:
            {
                "symbol": str,
                "deviation_pct": float,
                "highest_price": float,
                "lowest_price": float,
                "highest_venue": str,
                "lowest_venue": str,
                "venues": [
                    {"venue": str, "price": float, "timestamp": str}
                ],
                "cross_asset": Optional[dict],
            }
            veya None (sapma yoksa)
        """
        prices = self._fetch_multi_venue(symbol)
        if len(prices) < 2:
            return None

        price_values = [p["price"] for p in prices if p["price"] > 0]
        if len(price_values) < 2:
            return None

        max_price = max(price_values)
        min_price = min(price_values)
        if max_price <= 0:
            return None

        deviation = (max_price - min_price) / max_price
        if deviation < self.deviation_threshold:
            return None

        highest = next(p for p in prices if p["price"] == max_price)
        lowest = next(p for p in prices if p["price"] == min_price)

        result = {
            "symbol": symbol,
            "deviation_pct": round(deviation * 100, 2),
            "highest_price": round(max_price, 4),
            "lowest_price": round(min_price, 4),
            "highest_venue": highest["venue"],
            "lowest_venue": lowest["venue"],
            "venues": prices,
            "cross_asset": None,
        }

        # Cross-asset: USDTRY korelasyon bozulmasi
        cross = self._check_cross_asset(symbol)
        if cross:
            result["cross_asset"] = cross

        return result

    def _fetch_multi_venue(self, symbol: str) -> list[dict]:
        """
        FeedAggregator uzerinden tum kaynaklari dene.

        Donus: [{"venue": str, "price": float, "timestamp": str, "volume": float|None}]
        """
        venues = ["yahoo", "tradingview", "investing", "bigpara"]
        prices = []
        for venue in venues:
            try:
                df = self.feed.fetch(symbol, interval="1d", period="1d", preferred=venue)
                if df is not None and not df.empty:
                    last_row = df.iloc[-1]
                    price = float(last_row.get("close", last_row.get("Close", 0)))
                    ts = str(last_row.name) if hasattr(last_row, "name") else str(pd.Timestamp.now())
                    vol = last_row.get("volume", last_row.get("Volume", None))
                    prices.append({
                        "venue": venue,
                        "price": price,
                        "timestamp": ts,
                        "volume": float(vol) if vol is not None else None,
                    })
            except Exception:
                continue
        return prices

    def _check_cross_asset(self, symbol: str) -> Optional[dict]:
        """
        THYAO/USDTRY korelasyon bozulmasi gibi cross-asset arbitraj.

        Donus: {"type": str, "description": str, "score": float}
        """
        # THYAO gibi hisselerin USD bazli fiyatini hesapla
        if not symbol.endswith(".IS"):
            symbol_local = symbol + ".IS"
        else:
            symbol_local = symbol

        try:
            stock_df = self.feed.fetch(symbol_local, interval="1d", period="5d")
            usdtry_df = self.feed.fetch("USDTRY=X", interval="1d", period="5d")
            if stock_df is None or usdtry_df is None or stock_df.empty or usdtry_df.empty:
                return None

            stock_close = stock_df["close"].astype(float)
            usdtry_close = usdtry_df["close"].astype(float)

            # Son 5 gunluk korelasyon
            min_len = min(len(stock_close), len(usdtry_close))
            if min_len < 3:
                return None

            corr = np.corrcoef(stock_close.iloc[-min_len:].values, usdtry_close.iloc[-min_len:].values)[0, 1]
            if np.isnan(corr):
                return None

            # Korelasyon bozulmasi: normalde THYAO ile USDTRY negatif korele olabilir
            # Eger korelasyon sifira yaklasiyorsa veya pozitife donuyorsa = bozulma
            if abs(corr) < 0.3:
                return {
                    "type": "correlation_breakdown",
                    "description": f"{symbol} ile USDTRY korelasyonu bozuldu ({corr:.2f})",
                    "score": round(float(1 - abs(corr)), 2),
                }
        except Exception:
            pass

        return None

    def scan_universe(self, symbols: list[str]) -> list[dict]:
        """
        Hisse listesi uzerinde toplu arbitraj taramasi.

        Donus: arbitraj firsati olanlarin listesi (sirali: en yuksek sapma once)
        """
        results = []
        for sym in symbols:
            opp = self.check_symbol(sym)
            if opp:
                results.append(opp)

        results.sort(key=lambda x: x["deviation_pct"], reverse=True)
        return results

    def format_alert(self, opp: dict) -> str:
        """
        Telegram alert mesaji olustur.
        """
        lines = [
            f"Arbitraj Uyari: {opp['symbol']}",
            f"Sapma: %{opp['deviation_pct']}",
            f"Yuksek: {opp['highest_price']} ({opp['highest_venue']})",
            f"Dusuk: {opp['lowest_price']} ({opp['lowest_venue']})",
        ]
        cross = opp.get("cross_asset")
        if cross:
            lines.append(f"Cross-Asset: {cross['description']}")
        lines.append("K145: Bilgi amacli, dogrudan islem yapilmaz.")
        return "\n".join(lines)


if __name__ == "__main__":
    det = ArbitrageDetector(deviation_threshold_pct=0.5)
    # Demo: THYAO (gercek HTTP cagrilar yapar)
    result = det.check_symbol("THYAO")
    if result:
        print(det.format_alert(result))
    else:
        print("THYAO icin arbitraj firsati bulunamadi.")
