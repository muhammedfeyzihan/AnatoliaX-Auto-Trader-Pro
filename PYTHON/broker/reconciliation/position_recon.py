"""
reconciliation/position_recon.py — Konum uzlastirma motoru
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List


@dataclass
class ReconciliationDiff:
    symbol: str
    expected: Decimal
    actual: Decimal
    diff: Decimal


class ReconciliationEngine:
    """
    Gun sonu konum uzlastirma.

    Surec:
    1. Broker'dan konumlari cek
    2. Dahili kayitlarla karsilastir
    3. Farklari raporla
    4. 3 gun ust uste tutarsizlik varsa: Insan onayi ile duzeltme
    """

    def __init__(self):
        self._internal: Dict[str, Decimal] = {}
        self._history: List[Dict] = []

    def set_internal(self, positions: Dict[str, Decimal]) -> None:
        self._internal = positions

    def reconcile(self, broker_positions: Dict[str, Decimal]) -> List[ReconciliationDiff]:
        diffs = []
        all_symbols = set(self._internal.keys()) | set(broker_positions.keys())
        for sym in all_symbols:
            exp = self._internal.get(sym, Decimal("0"))
            act = broker_positions.get(sym, Decimal("0"))
            if exp != act:
                diffs.append(ReconciliationDiff(symbol=sym, expected=exp, actual=act, diff=act - exp))
        self._history.append({"diffs": diffs, "timestamp": "2026-05-26T18:00:00Z"})
        return diffs

    def requires_human_review(self, consecutive_days: int = 3) -> bool:
        """3 gun ust uste fark varsa insan onayi gerektirir."""
        return len(self._history) >= consecutive_days and all(bool(day.get("diffs")) for day in self._history[-consecutive_days:])
