"""
macro_fetcher.py — Makroekonomik Veri Cekme
Fed, DXY, CPI/TUFE, TCMB faiz, USD/TRY, Altin, Petrol, VIX

Kullanim:
    from data.macro_fetcher import MacroFetcher
    fetcher = MacroFetcher()
    macro = fetcher.fetch_all()
    print(macro)
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
from datetime import datetime
from typing import Dict, Optional


class MacroFetcher:
    """
    Ucretsiz API'lerden makroekonomik veri cekme.
    - DXY (Dolar Endeksi): tradingeconomics.com / yfinance (DX-Y.NYB)
    - USD/TRY: yfinance (USDTRY=X)
    - VIX: yfinance (^VIX)
    - Altin: yfinance (GC=F)
    - Petrol: yfinance (CL=F)
    - TCMB Faiz: tcmb.gov.tr (placeholder)
    - TÜFE/CPI: tradingeconomics.com / tuik.gov.tr (placeholder)
    - Fed Faiz: tradingeconomics.com (placeholder)
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def fetch_usdtry(self) -> dict:
        """USD/TRY kurunu cek."""
        try:
            url = "https://api.exchangerate-api.com/v4/latest/USD"
            resp = self.session.get(url, timeout=30)
            data = resp.json()
            rate = data.get("rates", {}).get("TRY", 0.0)
            return {
                "indicator": "USDTRY",
                "value": rate,
                "unit": "TL",
                "timestamp": datetime.now().isoformat(),
                "source": "exchangerate-api",
                "note": "Guncel kur",
            }
        except Exception as e:
            return {"indicator": "USDTRY", "value": 0.0, "error": str(e), "timestamp": datetime.now().isoformat()}

    def fetch_dxy(self) -> dict:
        """Dolar Endeksi (DXY) cek."""
        try:
            # yfinance ile DXY (DX-Y.NYB)
            import yfinance as yf
            ticker = yf.Ticker("DX-Y.NYB")
            hist = ticker.history(period="5d")
            if not hist.empty:
                last = hist.iloc[-1]
                return {
                    "indicator": "DXY",
                    "value": round(float(last["Close"]), 2),
                    "unit": "index",
                    "timestamp": datetime.now().isoformat(),
                    "source": "yfinance",
                    "note": "Son 5 gunluk ortalama yok, son kapanis",
                }
        except Exception as e:
            pass
        return {"indicator": "DXY", "value": 0.0, "error": "Cekilemedi", "timestamp": datetime.now().isoformat()}

    def fetch_vix(self) -> dict:
        """VIX (Korku endeksi) cek."""
        try:
            import yfinance as yf
            ticker = yf.Ticker("^VIX")
            hist = ticker.history(period="5d")
            if not hist.empty:
                last = hist.iloc[-1]
                return {
                    "indicator": "VIX",
                    "value": round(float(last["Close"]), 2),
                    "unit": "index",
                    "timestamp": datetime.now().isoformat(),
                    "source": "yfinance",
                    "note": "Volatilite endeksi",
                }
        except Exception:
            pass
        return {"indicator": "VIX", "value": 0.0, "error": "Cekilemedi", "timestamp": datetime.now().isoformat()}

    def fetch_gold(self) -> dict:
        """Altin fiyati (USD/ons) cek."""
        try:
            import yfinance as yf
            ticker = yf.Ticker("GC=F")
            hist = ticker.history(period="5d")
            if not hist.empty:
                last = hist.iloc[-1]
                return {
                    "indicator": "GOLD",
                    "value": round(float(last["Close"]), 2),
                    "unit": "USD/ons",
                    "timestamp": datetime.now().isoformat(),
                    "source": "yfinance",
                    "note": "Spot altin",
                }
        except Exception:
            pass
        return {"indicator": "GOLD", "value": 0.0, "error": "Cekilemedi", "timestamp": datetime.now().isoformat()}

    def fetch_brent(self) -> dict:
        """Brent petrol fiyati cek."""
        try:
            import yfinance as yf
            ticker = yf.Ticker("BZ=F")
            hist = ticker.history(period="5d")
            if not hist.empty:
                last = hist.iloc[-1]
                return {
                    "indicator": "BRENT",
                    "value": round(float(last["Close"]), 2),
                    "unit": "USD/varil",
                    "timestamp": datetime.now().isoformat(),
                    "source": "yfinance",
                    "note": "Brent petrol",
                }
        except Exception:
            pass
        return {"indicator": "BRENT", "value": 0.0, "error": "Cekilemedi", "timestamp": datetime.now().isoformat()}

    def fetch_bist100(self) -> dict:
        """BIST 100 endeks degeri cek."""
        try:
            import yfinance as yf
            ticker = yf.Ticker("XU100.IS")
            hist = ticker.history(period="5d")
            if not hist.empty:
                last = hist.iloc[-1]
                return {
                    "indicator": "BIST100",
                    "value": round(float(last["Close"]), 2),
                    "unit": "puan",
                    "timestamp": datetime.now().isoformat(),
                    "source": "yfinance",
                    "note": "BIST 100 endeksi",
                }
        except Exception:
            pass
        return {"indicator": "BIST100", "value": 0.0, "error": "Cekilemedi", "timestamp": datetime.now().isoformat()}

    def fetch_tcmb_rate(self) -> dict:
        """TCMB politika faizi.
        Gercek entegrasyon: TCMB EVDS API'si (evds2.tcmb.gov.tr) kullanilabilir.
        Simdilik .env veya varsayilan deger ile calisir.
        """
        import os
        value = os.getenv("TCMB_RATE", "50.0")
        try:
            value = float(value)
        except ValueError:
            value = 50.0
        return {
            "indicator": "TCMB_RATE",
            "value": value,
            "unit": "%",
            "timestamp": datetime.now().isoformat(),
            "source": "placeholder",
            "note": "TCMB politika faizi (.env TCMB_RATE ile override edilebilir)",
        }

    def fetch_inflation(self) -> dict:
        """TÜFE yillik degisim.
        Gercek entegrasyon: TÜIK API veya EVDS.
        Simdilik .env veya varsayilan deger ile calisir.
        """
        import os
        value = os.getenv("TUFe_RATE", "0.0")
        try:
            value = float(value)
        except ValueError:
            value = 0.0
        return {
            "indicator": "TUFe",
            "value": value,
            "unit": "%",
            "timestamp": datetime.now().isoformat(),
            "source": "placeholder",
            "note": "TÜFE yillik degisim (.env TUFe_RATE ile override edilebilir)",
        }

    def fetch_all(self) -> pd.DataFrame:
        """
        Tum makro verileri cek ve DataFrame olarak dondur.
        Returns: DataFrame(indicator, value, unit, timestamp, source, note)
        """
        indicators = [
            self.fetch_usdtry(),
            self.fetch_dxy(),
            self.fetch_vix(),
            self.fetch_gold(),
            self.fetch_brent(),
            self.fetch_bist100(),
            self.fetch_tcmb_rate(),
            self.fetch_inflation(),
        ]
        return pd.DataFrame(indicators)

    def get_regime_score(self) -> dict:
        """
        Makro verilere gore piyasa rejimi skoru hesapla.
        Returns: {"regime": "BULL|BEAR|NEUTRAL", "score": float, "factors": dict}
        """
        df = self.fetch_all()
        factors = {}

        # USD/TRY yukseliyor mu?
        usd = df[df["indicator"] == "USDTRY"]["value"].values
        factors["usdtry_rising"] = bool(usd[0] > 30) if len(usd) > 0 else False

        # VIX yuksek mi? (>25 = stresli)
        vix = df[df["indicator"] == "VIX"]["value"].values
        factors["vix_high"] = bool(vix[0] > 25) if len(vix) > 0 else False

        # BIST100 yukseliyor mu?
        bist = df[df["indicator"] == "BIST100"]["value"].values
        factors["bist_rising"] = bool(bist[0] > 10000) if len(bist) > 0 else False

        # Rejim skoru
        score = 0
        if factors.get("bist_rising"):
            score += 1
        if not factors.get("vix_high"):
            score += 1
        if not factors.get("usdtry_rising"):
            score += 1

        if score >= 2:
            regime = "BULL"
        elif score == 1:
            regime = "NEUTRAL"
        else:
            regime = "BEAR"

        return {"regime": regime, "score": score, "factors": factors}


if __name__ == "__main__":
    fetcher = MacroFetcher()
    df = fetcher.fetch_all()
    print(df.to_string(index=False))
    regime = fetcher.get_regime_score()
    print(f"Rejim: {regime}")
