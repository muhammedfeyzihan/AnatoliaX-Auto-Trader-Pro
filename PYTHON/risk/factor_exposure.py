"""
risk/factor_exposure.py — Factor Exposure Engine (Phase 3)
Module 11 from anatoliax_prompt_v6.txt

Features:
  - Factor model: r_p = alpha + sum(beta_k * F_k) + epsilon
  - Factors: market_beta, sector_momentum, volatility_factor, momentum_factor, macro_rates, macro_fx, macro_commodities
  - Barra-style multi-factor regression or PCA on returns
  - Risk decomposition: sigma_p^2 = sum(sum(beta_i*beta_j*Cov(F_i,F_j))) + sigma_epsilon^2
"""

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class FactorExposureResult:
    alpha: float = 0.0
    betas: Dict[str, float] = field(default_factory=dict)
    factor_pnl: Dict[str, float] = field(default_factory=dict)
    residual_variance: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FactorExposureEngine:
    """
    Barra-style multi-factor exposure engine.
    """

    FACTORS = [
        "market_beta",
        "sector_momentum",
        "volatility_factor",
        "momentum_factor",
        "macro_rates",
        "macro_fx",
        "macro_commodities",
    ]

    def __init__(self):
        self._factor_returns: Dict[str, List[float]] = {f: [] for f in self.FACTORS}
        self._portfolio_returns: List[float] = []

    def ingest(self, portfolio_return: float, factor_returns: Dict[str, float]):
        self._portfolio_returns.append(portfolio_return)
        for f, r in factor_returns.items():
            if f in self._factor_returns:
                self._factor_returns[f].append(r)

    def estimate_betas(self, window: int = 60) -> Dict[str, float]:
        """Simple OLS-style beta estimation: beta = Cov(r_p, F_k) / Var(F_k)."""
        betas = {}
        p = self._portfolio_returns[-window:]
        if len(p) < 2:
            return betas
        p_mean = statistics.mean(p)
        for f in self.FACTORS:
            f_rets = self._factor_returns[f][-window:]
            if len(f_rets) < 2:
                continue
            f_mean = statistics.mean(f_rets)
            cov = sum((pi - p_mean) * (fi - f_mean) for pi, fi in zip(p, f_rets)) / (len(p) - 1)
            var = sum((fi - f_mean) ** 2 for fi in f_rets) / (len(f_rets) - 1)
            betas[f] = cov / var if var != 0 else 0.0
        return betas

    def decompose_risk(self, betas: Dict[str, float], window: int = 60) -> Dict:
        """sigma_p^2 = sum(sum(beta_i*beta_j*Cov(F_i,F_j))) + sigma_epsilon^2."""
        factor_var = {}
        for f in self.FACTORS:
            rets = self._factor_returns[f][-window:]
            if len(rets) >= 2:
                factor_var[f] = statistics.variance(rets)
            else:
                factor_var[f] = 0.0

        systematic = 0.0
        for fi in self.FACTORS:
            for fj in self.FACTORS:
                if fi in betas and fj in betas:
                    cov = factor_var.get(fi, 0.0) if fi == fj else 0.0  # simplified
                    systematic += betas[fi] * betas[fj] * cov

        p = self._portfolio_returns[-window:]
        total_var = statistics.variance(p) if len(p) >= 2 else 0.0
        residual = max(0.0, total_var - systematic)

        return {
            "total_variance": total_var,
            "systematic_variance": systematic,
            "residual_variance": residual,
            "factor_variances": factor_var,
        }

    def get_exposure_report(self) -> FactorExposureResult:
        betas = self.estimate_betas()
        risk = self.decompose_risk(betas)
        factor_pnl = {f: betas.get(f, 0.0) * statistics.mean(self._factor_returns[f][-60:]) if self._factor_returns[f] else 0.0 for f in self.FACTORS}
        return FactorExposureResult(
            betas=betas,
            factor_pnl=factor_pnl,
            residual_variance=risk["residual_variance"],
        )
