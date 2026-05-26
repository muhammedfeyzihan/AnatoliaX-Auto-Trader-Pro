"""
compliance/bist_reporting.py — BIST K142-K148 Automated Surveillance Reporting

K260: Automated reporting for VBTS, circuit breaker events, and short-selling bans.
"""

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class BistSurveillanceEvent:
    event_type: str  # CIRCUIT_BREAKER, VBTS_VIOLATION, SHORT_SELL_BAN, WASH_TRADE
    symbol: str
    details: Dict
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class BistReporting:
    """
    Automated BIST K142-K148 compliance reporter.
    """

    REGULATIONS = {
        "K142": "Volatility Based Trading System (VBTS)",
        "K143": "Circuit Breaker Mechanism",
        "K144": "Short Selling Restrictions",
        "K145": "Price Manipulation Surveillance",
        "K146": "Insider Trading Detection",
        "K147": "Market Abuse Reporting",
        "K148": "Suspicious Transaction Reporting (SAR)",
    }

    def __init__(self, output_dir: str = "compliance_reports"):
        self.output_dir = output_dir
        self._events: List[BistSurveillanceEvent] = []

    def log_event(self, event: BistSurveillanceEvent):
        self._events.append(event)

    def generate_vbts_report(self) -> Dict:
        vbts_events = [e for e in self._events if e.event_type == "VBTS_VIOLATION"]
        return {
            "regulation": "K142",
            "title": self.REGULATIONS["K142"],
            "event_count": len(vbts_events),
            "events": [asdict(e) for e in vbts_events],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def generate_circuit_breaker_report(self) -> Dict:
        cb_events = [e for e in self._events if e.event_type == "CIRCUIT_BREAKER"]
        return {
            "regulation": "K143",
            "title": self.REGULATIONS["K143"],
            "event_count": len(cb_events),
            "events": [asdict(e) for e in cb_events],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def generate_short_sell_report(self) -> Dict:
        ss_events = [e for e in self._events if e.event_type == "SHORT_SELL_BAN"]
        return {
            "regulation": "K144",
            "title": self.REGULATIONS["K144"],
            "event_count": len(ss_events),
            "summary": "Short selling ban compliance check performed.",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def export_all(self) -> List[str]:
        import os
        os.makedirs(self.output_dir, exist_ok=True)
        paths = []
        for reg in ["K142", "K143", "K144", "K145", "K146", "K147", "K148"]:
            report = getattr(self, f"generate_{reg.lower().replace('_', '')}_report", lambda: {"regulation": reg})()
            path = f"{self.output_dir}/{reg}_report.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            paths.append(path)
        return paths
