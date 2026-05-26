"""
paper_live_separator.py — Paper/Live Separator + Execution Quality Score
K179-K183: Paper/live dual engine, latency monitoring, PnL reconciliation, EQS.
"""

import time
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable


@dataclass
class ExecutionOutcome:
    signal_id: str
    symbol: str
    side: str
    size: float
    expected_price: float
    filled_price: float
    latency_ms: float
    fill_rate: float
    slippage: float
    market_impact: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionQualityScore:
    """
    Execution Quality Score (EQS) hesaplama.
    EQS = w1*fill_rate + w2*(1-slippage/price) + w3*(1-latency/max_latency) + w4*(1-market_impact)
    """

    def __init__(
        self,
        max_latency_ms: float = 500.0,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.max_latency_ms = max_latency_ms
        self.weights = weights or {
            "fill_rate": 0.30,
            "slippage": 0.25,
            "latency": 0.25,
            "market_impact": 0.20,
        }

    def calculate(
        self,
        fill_rate: float,
        avg_slippage: float,
        latency_ms: float,
        market_impact: float,
    ) -> float:
        """
        0-100 arası EQS hesapla.
        """
        fill_score = fill_rate
        slippage_score = max(0, 1 - avg_slippage)
        latency_score = max(0, 1 - (latency_ms / self.max_latency_ms))
        impact_score = max(0, 1 - market_impact)

        eqs = (
            self.weights["fill_rate"] * fill_score +
            self.weights["slippage"] * slippage_score +
            self.weights["latency"] * latency_score +
            self.weights["market_impact"] * impact_score
        )
        return round(eqs * 100, 2)


class PaperLiveSeparator:
    """
    Paper ve live trading sonuçlarını ayrı ayrı tutan, karşılaştıran motor.
    """

    def __init__(self, max_latency_ms: float = 500.0):
        self.max_latency_ms = max_latency_ms
        self.eqs_calculator = ExecutionQualityScore(max_latency_ms)
        self._paper_outcomes: List[ExecutionOutcome] = []
        self._live_outcomes: List[ExecutionOutcome] = []
        self._latency_samples: List[float] = []

    # ── Paper Trading (K179) ─────────────────────────────

    def run_paper(self, signal: dict) -> ExecutionOutcome:
        """
        Paper trade: ideal fiyat, anlık dolum, zero latency.
        """
        outcome = ExecutionOutcome(
            signal_id=signal.get("id", "paper_" + str(len(self._paper_outcomes))),
            symbol=signal.get("symbol", ""),
            side=signal.get("side", "BUY"),
            size=signal.get("size", 0.0),
            expected_price=signal.get("price", 0.0),
            filled_price=signal.get("price", 0.0),
            latency_ms=0.0,
            fill_rate=1.0,
            slippage=0.0,
            market_impact=0.0,
        )
        self._paper_outcomes.append(outcome)
        return outcome

    # ── Live Trading (K179) ──────────────────────────────

    def run_live(self, signal: dict, filled_price: float, latency_ms: float, fill_rate: float = 1.0) -> ExecutionOutcome:
        """
        Live trade: gerçek fiyat, latency, fill rate.
        """
        expected = signal.get("price", filled_price)
        slippage = abs(filled_price - expected) / expected if expected > 0 else 0.0

        outcome = ExecutionOutcome(
            signal_id=signal.get("id", "live_" + str(len(self._live_outcomes))),
            symbol=signal.get("symbol", ""),
            side=signal.get("side", "BUY"),
            size=signal.get("size", 0.0),
            expected_price=expected,
            filled_price=filled_price,
            latency_ms=latency_ms,
            fill_rate=fill_rate,
            slippage=slippage,
            market_impact=signal.get("market_impact", 0.0),
        )
        self._live_outcomes.append(outcome)
        self._latency_samples.append(latency_ms)
        return outcome

    # ── Latency Monitoring (K181) ──────────────────────────

    def latency_stats(self) -> dict:
        """
        Live latency P50/P95/P99.
        """
        if not self._latency_samples:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "count": 0}
        sorted_lat = sorted(self._latency_samples)
        n = len(sorted_lat)
        p50 = sorted_lat[n // 2]
        p95_idx = int(n * 0.95)
        p99_idx = int(n * 0.99)
        return {
            "p50": round(p50, 2),
            "p95": round(sorted_lat[min(p95_idx, n - 1)], 2),
            "p99": round(sorted_lat[min(p99_idx, n - 1)], 2),
            "count": n,
        }

    # ── PnL Reconciliation (K180) ────────────────────────

    def _pnl(self, outcome: ExecutionOutcome) -> float:
        """Bir outcome'un PnL'ini hesapla."""
        if outcome.side == "BUY":
            return (outcome.filled_price - outcome.expected_price) * outcome.size
        return (outcome.expected_price - outcome.filled_price) * outcome.size

    def reconcile(self) -> dict:
        """
        Paper vs Live PnL karşılaştırması.
        Aynı signal_id ile paper/live outcome'ları eşleştirir.
        """
        if not self._paper_outcomes or not self._live_outcomes:
            return {"difference_pct": None, "alert": False, "reason": "No data", "pairs": []}

        paper_by_id = {o.signal_id: o for o in self._paper_outcomes}
        live_by_id = {o.signal_id: o for o in self._live_outcomes}

        pairs = []
        total_paper_pnl = 0.0
        total_live_pnl = 0.0
        mismatches = 0

        for sid in set(paper_by_id.keys()) | set(live_by_id.keys()):
            paper_o = paper_by_id.get(sid)
            live_o = live_by_id.get(sid)
            if paper_o and live_o:
                paper_pnl = self._pnl(paper_o)
                live_pnl = self._pnl(live_o)
                total_paper_pnl += paper_pnl
                total_live_pnl += live_pnl
                if paper_pnl != 0:
                    diff_pct = abs((live_pnl - paper_pnl) / paper_pnl)
                else:
                    diff_pct = abs(live_pnl) * 100 if live_pnl != 0 else 0.0
                pairs.append({
                    "signal_id": sid,
                    "paper_pnl": round(paper_pnl, 4),
                    "live_pnl": round(live_pnl, 4),
                    "diff_pct": round(diff_pct * 100, 4),
                    "alert": diff_pct > 0.01,
                })
            else:
                mismatches += 1

        if total_paper_pnl == 0:
            overall_diff_pct = 0.0 if total_live_pnl == 0 else float("inf")
        else:
            overall_diff_pct = abs((total_live_pnl - total_paper_pnl) / total_paper_pnl)

        alert = overall_diff_pct > 0.01  # > 1% difference

        return {
            "paper_pnl": round(total_paper_pnl, 2),
            "live_pnl": round(total_live_pnl, 2),
            "difference_pct": round(overall_diff_pct * 100, 4),
            "alert": alert,
            "reason": f"Paper/Live PnL diff {overall_diff_pct*100:.2f}%" if alert else "PnL aligned",
            "pairs": pairs,
            "mismatches": mismatches,
        }

    # ── EQS Calculation (K182-K183) ──────────────────────

    def calculate_eqs(self, outcomes: List[ExecutionOutcome] = None) -> float:
        """
        Verilen outcome'lar için EQS hesapla.
        """
        if outcomes is None:
            outcomes = self._live_outcomes
        if not outcomes:
            return 0.0

        avg_slippage = statistics.mean([o.slippage for o in outcomes])
        avg_latency = statistics.mean([o.latency_ms for o in outcomes])
        avg_fill_rate = statistics.mean([o.fill_rate for o in outcomes])
        avg_impact = statistics.mean([o.market_impact for o in outcomes])

        return self.eqs_calculator.calculate(
            fill_rate=avg_fill_rate,
            avg_slippage=avg_slippage,
            latency_ms=avg_latency,
            market_impact=avg_impact,
        )

    def daily_summary(self) -> dict:
        """Günlük paper/live özet."""
        recon = self.reconcile()
        eqs = self.calculate_eqs()
        latency = self.latency_stats()
        return {
            "paper_trades": len(self._paper_outcomes),
            "live_trades": len(self._live_outcomes),
            "reconciliation": recon,
            "eqs": eqs,
            "latency": latency,
        }
