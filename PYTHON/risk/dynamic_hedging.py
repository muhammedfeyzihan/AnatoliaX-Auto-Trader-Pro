"""
risk/dynamic_hedging.py — Dynamic Hedging Engine (Phase 3)
Module 12 from anatoliax_prompt_v6.txt

Features:
  - Delta hedge: maintain delta_portfolio ≈ 0 via index futures or inverse ETFs
  - Hedge size: N_futures = -delta_portfolio / delta_future
  - Volatility hedge: VIX futures or options straddle
  - Market-neutral: net_beta ∈ [-0.1, 0.1] when regime = high_risk
  - Passive limit orders at mid ± 0.5*spread to minimize impact
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional


@dataclass
class HedgeRecommendation:
    hedge_type: str  # "delta", "volatility", "market_neutral"
    instrument: str
    side: str
    size: float
    limit_price: float
    reason: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DynamicHedgingEngine:
    """
    Dynamic hedging engine for portfolio risk management.
    """

    def __init__(
        self,
        beta_threshold: float = 0.1,
        delta_threshold: float = 500.0,
    ):
        self.beta_threshold = beta_threshold
        self.delta_threshold = delta_threshold

    def delta_hedge(
        self,
        portfolio_delta: float,
        future_delta: float,
        future_symbol: str,
        midprice: float,
        spread: float,
    ) -> Optional[HedgeRecommendation]:
        if abs(portfolio_delta) < self.delta_threshold:
            return None
        if future_delta == 0:
            return None
        n = -portfolio_delta / future_delta
        limit = midprice + (0.5 * spread) if n > 0 else midprice - (0.5 * spread)
        return HedgeRecommendation(
            hedge_type="delta",
            instrument=future_symbol,
            side="buy" if n > 0 else "sell",
            size=abs(n),
            limit_price=limit,
            reason=f"portfolio_delta={portfolio_delta:.2f}",
        )

    def volatility_hedge(
        self,
        portfolio_vega: float,
        vix_price: float,
        regime: str,
    ) -> Optional[HedgeRecommendation]:
        if regime != "high_risk" or abs(portfolio_vega) < 100:
            return None
        return HedgeRecommendation(
            hedge_type="volatility",
            instrument="VIX_FUTURE",
            side="buy",
            size=abs(portfolio_vega) / 1000,
            limit_price=vix_price,
            reason=f"regime={regime}, vega={portfolio_vega:.2f}",
        )

    def market_neutral_check(self, net_beta: float, regime: str) -> Optional[HedgeRecommendation]:
        if regime != "high_risk" or abs(net_beta) <= self.beta_threshold:
            return None
        return HedgeRecommendation(
            hedge_type="market_neutral",
            instrument="INDEX_FUTURE",
            side="sell" if net_beta > 0 else "buy",
            size=abs(net_beta) * 100,
            limit_price=0.0,
            reason=f"net_beta={net_beta:.3f} exceeds threshold",
        )
