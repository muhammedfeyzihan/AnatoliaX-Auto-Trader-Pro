"""
fundamental_filter.py — Fundamental Analysis Filter
K163-K166: P/E, P/B, EV/EBITDA vs sector, 3-year trend, KAP events.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone


@dataclass
class FundamentalData:
    symbol: str
    sector: str
    pe: Optional[float] = None
    pb: Optional[float] = None
    ev_ebitda: Optional[float] = None
    net_profit_growth_3y: Optional[float] = None
    debt_to_equity: Optional[float] = None
    ebitda_margin: Optional[float] = None


class FundamentalFilter:
    """
    Teknik sinyalleri temel analiz verileriyle filtreleyen motor.
    """

    def __init__(self, kap_fetcher=None, instrument_provider=None):
        self.kap_fetcher = kap_fetcher
        self.instrument_provider = instrument_provider
        # Sektör ortalamaları (mock/varsayılan)
        self._sector_benchmarks: Dict[str, dict] = {}

    def set_sector_benchmark(self, sector: str, pe: float, pb: float, ev_ebitda: float):
        """Sektör ortalamalarını manuel ayarla."""
        self._sector_benchmarks[sector] = {
            "pe": pe,
            "pb": pb,
            "ev_ebitda": ev_ebitda,
        }

    # ── Skorlama (K163-K164) ─────────────────────────────

    def score(self, data: FundamentalData) -> dict:
        """
        0-100 arası temel analiz skoru hesapla.
        """
        checks = {}
        score = 0
        max_points = 0

        benchmark = self._sector_benchmarks.get(data.sector, {})

        # P/E vs sector
        if data.pe is not None and benchmark.get("pe"):
            max_points += 25
            pe_ok = data.pe < benchmark["pe"] * 1.2
            checks["pe"] = {"value": data.pe, "threshold": benchmark["pe"] * 1.2, "pass": pe_ok}
            if pe_ok:
                score += 25

        # P/B vs sector
        if data.pb is not None and benchmark.get("pb"):
            max_points += 25
            pb_ok = data.pb < benchmark["pb"] * 1.3
            checks["pb"] = {"value": data.pb, "threshold": benchmark["pb"] * 1.3, "pass": pb_ok}
            if pb_ok:
                score += 25

        # EV/EBITDA vs sector
        if data.ev_ebitda is not None and benchmark.get("ev_ebitda"):
            max_points += 25
            ev_ok = data.ev_ebitda < benchmark["ev_ebitda"] * 1.2
            checks["ev_ebitda"] = {"value": data.ev_ebitda, "threshold": benchmark["ev_ebitda"] * 1.2, "pass": ev_ok}
            if ev_ok:
                score += 25

        # 3-year net profit growth
        if data.net_profit_growth_3y is not None:
            max_points += 25
            growth_ok = data.net_profit_growth_3y >= 0.05  # %5/year
            checks["net_profit_growth"] = {"value": data.net_profit_growth_3y, "threshold": 0.05, "pass": growth_ok}
            if growth_ok:
                score += 25

        final_score = int((score / max_points) * 100) if max_points > 0 else 50
        return {
            "score": final_score,
            "checks": checks,
            "pass": final_score >= 40,
        }

    # ── KAP Olayları (K165) ──────────────────────────────

    def check_kap_events(self, symbol: str, days: int = 30) -> dict:
        """
        Son N gündeki KAP bildirimlerini kontrol et.
        Returns: yeşil/sarı/kırmızı ışık.
        """
        if self.kap_fetcher is None:
            return {"status": "UNKNOWN", "events": [], "reason": "No KAP fetcher configured"}

        try:
            df = self.kap_fetcher.fetch_recent(days=days)
            if df.empty:
                return {"status": "NEUTRAL", "events": [], "reason": "No KAP events"}

            sym_df = df[df["ticker"] == symbol.upper()]
            events = sym_df.to_dict("records")

            types = sym_df["type"].unique().tolist() if not sym_df.empty else []

            if any(t in types for t in ["SERMAYE", "TEMETDU"]):
                status = "GREEN"
            elif "YONETIM" in types:
                status = "YELLOW"
            else:
                status = "NEUTRAL"

            return {
                "status": status,
                "events": events[:5],
                "types": types,
            }
        except Exception as e:
            return {"status": "ERROR", "events": [], "reason": str(e)}

    # ── Filtreleme (K166) ─────────────────────────────────

    def filter_signals(
        self,
        signals: List[dict],
        min_score: int = 40,
    ) -> List[dict]:
        """
        Sinyal listesini temel analiz skoruna göre filtrele.
        """
        filtered = []
        for sig in signals:
            data = sig.get("fundamental")
            if data is None:
                # No fundamental data → pass through with warning
                sig["fundamental_pass"] = True
                sig["fundamental_score"] = None
                filtered.append(sig)
                continue

            if isinstance(data, dict):
                data = FundamentalData(**data)

            result = self.score(data)
            sig["fundamental_pass"] = result["pass"] and result["score"] >= min_score
            sig["fundamental_score"] = result["score"]
            sig["fundamental_checks"] = result["checks"]

            if sig["fundamental_pass"]:
                filtered.append(sig)

        return filtered
