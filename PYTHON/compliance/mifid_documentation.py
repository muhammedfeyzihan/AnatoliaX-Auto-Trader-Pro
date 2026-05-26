"""
compliance/mifid_documentation.py — MiFID II RTS 6 Algorithm Testing Documentation

K258: Algorithm testing must be documented with pre-trade controls,
kill functionality, and real-time monitoring evidence.
"""

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class AlgorithmTestRecord:
    algorithm_id: str
    version: str
    test_type: str  # "unit", "integration", "stress", "adversarial"
    description: str
    expected_behavior: str
    actual_behavior: str
    passed: bool
    evidence: Dict  # logs, screenshots, metrics
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class KillSwitchTest:
    trigger_condition: str
    kill_latency_ms: float
    positions_flattened: bool
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MifidDocumentation:
    """
    Generates MiFID II RTS 6 compliant algorithm testing documentation.
    """

    def __init__(self, output_path: str = "mifid_rts6_docs.json"):
        self.output_path = output_path
        self._records: List[AlgorithmTestRecord] = []
        self._kill_tests: List[KillSwitchTest] = []

    def record_test(self, record: AlgorithmTestRecord):
        self._records.append(record)

    def record_kill_switch_test(self, test: KillSwitchTest):
        self._kill_tests.append(test)

    def generate_report(self) -> Dict:
        """Generate RTS 6 compliance report."""
        total = len(self._records)
        passed = sum(1 for r in self._records if r.passed)
        return {
            "regulation": "MiFID II RTS 6",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "algorithm_tests": {
                "total": total,
                "passed": passed,
                "failed": total - passed,
                "pass_rate_pct": (passed / total * 100) if total > 0 else 0.0,
            },
            "kill_switch_tests": [asdict(k) for k in self._kill_tests],
            "pre_trade_controls": {
                "max_drawdown_limit": "5%",
                "max_position_limit": "10 lots",
                "max_daily_loss_limit": "3%",
                "real_time_monitoring": True,
            },
            "documentation_version": "1.0.0",
        }

    def export(self):
        report = self.generate_report()
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        return self.output_path
