"""
exposure_limiter.py — Tek hisse, toplam portfoy ve sektor limitleri
"""
from typing import Dict, List


class ExposureLimiter:
    """
    Tek hisse %2, toplam portfoy %10, sektor %20 limitleri.
    """

    def __init__(
        self,
        max_single_position_pct: float = 0.02,
        max_total_exposure_pct: float = 0.10,
        max_sector_pct: float = 0.20,
    ):
        self.max_single = max_single_position_pct
        self.max_total = max_total_exposure_pct
        self.max_sector = max_sector_pct

    def check(self, positions: List[dict], capital: float, sector_map: Dict[str, str] = None) -> dict:
        sector_map = sector_map or {}
        alerts = []
        total_exposure = 0.0
        sector_exposure: Dict[str, float] = {}

        for p in positions:
            symbol = p["symbol"]
            value = p.get("value", p.get("size", 0) * p.get("price", 0))
            total_exposure += value
            pct = value / capital if capital > 0 else 0

            if pct > self.max_single:
                alerts.append(f"POSITION_LIMIT: {symbol} %{pct*100:.2f} > %{self.max_single*100}")

            sector = sector_map.get(symbol, "UNKNOWN")
            sector_exposure[sector] = sector_exposure.get(sector, 0) + value

        total_pct = total_exposure / capital if capital > 0 else 0
        if total_pct > self.max_total:
            alerts.append(f"TOTAL_EXPOSURE: %{total_pct*100:.2f} > %{self.max_total*100}")

        for sector, value in sector_exposure.items():
            pct = value / capital if capital > 0 else 0
            if pct > self.max_sector:
                alerts.append(f"SECTOR_LIMIT: {sector} %{pct*100:.2f} > %{self.max_sector*100}")

        return {
            "total_exposure": total_exposure,
            "total_exposure_pct": total_pct,
            "alerts": alerts,
            "allowed": len(alerts) == 0,
        }
