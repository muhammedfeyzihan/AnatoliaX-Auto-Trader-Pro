"""
portfolio_optimizer.py — Markowitz Modern Portfolio Theory Optimizer
AutoTrader'dan entegre edilmistir.

Kullanim:
    from risk.portfolio_optimizer import PortfolioOptimizer
    opt = PortfolioOptimizer()
    result = opt.optimize(symbols=["THYAO", "GARAN", "ASELS", "TUPRS", "KCHOL"])
    # result: {"weights": {...}, "sharpe": 1.8, "frontier": [...]}
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


class PortfolioOptimizer:
    """
    Markowitz Modern Portfolio Theory ile optimal agirlik hesaplama.
    Kisitlar: max %2/hisse, max 5 hisse (AnatoliaX K kurallarina uygun).
    """

    def __init__(self, max_weight_pct: float = 2.0, max_stocks: int = 5):
        self.max_weight = max_weight_pct / 100.0  # Decimal
        self.max_stocks = max_stocks
        self.feed = FeedAggregator()

    def _fetch_returns(self, symbols: list[str], period: str = "6mo") -> pd.DataFrame:
        """Her hisse icin gunluk getiri DataFrame'i olustur."""
        returns = {}
        for sym in symbols:
            try:
                df = self.feed.fetch(sym, interval="1d", period=period)
                if not df.empty:
                    returns[sym] = df["close"].pct_change().dropna()
            except Exception:
                continue
        return pd.DataFrame(returns)

    def optimize(
        self,
        symbols: list[str],
        risk_free_rate: float = 0.10,  # BIST risksiz oran (yillik %10)
        period: str = "6mo",
    ) -> dict:
        """
        Verilen hisseler icin Markowitz optimal portfoy hesapla.

        Returns:
            {
                "weights": {"THYAO": 0.02, "GARAN": 0.02, ...},
                "sharpe": float,
                "expected_return": float,
                "volatility": float,
                "frontier": [(risk, ret) ...],
                "method": "markowitz" | "fallback_kelly"
            }
        """
        if len(symbols) < 2:
            return {"error": "En az 2 hisse gerekli", "weights": {}}

        returns_df = self._fetch_returns(symbols, period=period)
        if returns_df.empty or len(returns_df.columns) < 2:
            return {"error": "Veri cekilemedi", "weights": {}}

        # Yilliklandirilmis ortalama getiri ve kovaryans
        mean_returns = returns_df.mean() * 252
        cov_matrix = returns_df.cov() * 252

        n = len(mean_returns)
        if n == 0:
            return {"error": "Yeterli veri yok", "weights": {}}

        # Markowitz: Maksimum Sharpe Ratio portfoyu
        try:
            weights, sharpe, exp_ret, vol = self._max_sharpe_portfolio(
                mean_returns, cov_matrix, risk_free_rate
            )
        except Exception:
            # Fallback: esit agirlikli
            weights = np.ones(n) / n
            sharpe = 0.0
            exp_ret = mean_returns.mean()
            vol = np.sqrt(np.diag(cov_matrix).mean())

        # Kisitlara uygula: max %2/hisse, max 5 hisse
        weights_dict = self._apply_constraints(
            {sym: float(w) for sym, w in zip(mean_returns.index, weights)}
        )

        # Efficient frontier (ornekleme)
        frontier = self._efficient_frontier(mean_returns, cov_matrix, n_points=20)

        return {
            "weights": weights_dict,
            "sharpe": round(sharpe, 2),
            "expected_return": round(float(exp_ret), 4),
            "volatility": round(float(vol), 4),
            "frontier": frontier,
            "method": "markowitz",
        }

    def _max_sharpe_portfolio(
        self,
        mean_returns: pd.Series,
        cov_matrix: pd.DataFrame,
        risk_free_rate: float,
    ) -> tuple:
        """SciPy optimize ile maksimum Sharpe Ratio portfoyu bul."""
        import scipy.optimize as sco

        n = len(mean_returns)

        def _neg_sharpe(weights):
            p_ret = np.dot(weights, mean_returns)
            p_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            return -(p_ret - risk_free_rate) / (p_vol + 1e-8)

        # Kisitlar: agirliklar toplami = 1, her agirlik >= 0
        constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
        bounds = tuple((0.0, self.max_weight) for _ in range(n))
        init_guess = np.ones(n) / n

        result = sco.minimize(
            _neg_sharpe,
            init_guess,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        opt_w = result.x if result.success else init_guess
        p_ret = np.dot(opt_w, mean_returns)
        p_vol = np.sqrt(np.dot(opt_w.T, np.dot(cov_matrix, opt_w)))
        sharpe = (p_ret - risk_free_rate) / (p_vol + 1e-8)
        return opt_w, sharpe, p_ret, p_vol

    def _apply_constraints(self, weights: dict[str, float]) -> dict[str, float]:
        """
        AnatoliaX kisitlarini uygula:
        - Max %2/hisse
        - Max 5 hisse (geriye kalanlar siralanip ilk 5 alinir)
        - Normalizasyon YAPILMAZ: kalan kisim nakit (cash) olarak kalir.
          5 hisse x %2 = max %10 yatirim, geriye kalan %90 risksiz.
        """
        # Sirala, en yuksek agirlikli ilk 5'i al
        sorted_weights = dict(
            sorted(weights.items(), key=lambda x: x[1], reverse=True)[: self.max_stocks]
        )

        # Max %2 kisiti
        clipped = {k: round(min(v, self.max_weight), 4) for k, v in sorted_weights.items()}

        return clipped

    def _efficient_frontier(
        self,
        mean_returns: pd.Series,
        cov_matrix: pd.DataFrame,
        n_points: int = 20,
    ) -> list[tuple[float, float]]:
        """Efficient frontier noktalarini hesapla."""
        import scipy.optimize as sco

        n = len(mean_returns)
        bounds = tuple((0.0, self.max_weight) for _ in range(n))
        constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}

        target_returns = np.linspace(mean_returns.min(), mean_returns.max(), n_points)
        frontier = []

        for target in target_returns:
            # Minimize volatility for target return
            def _portfolio_vol(w):
                return np.sqrt(np.dot(w.T, np.dot(cov_matrix, w)))

            target_constraint = {
                "type": "eq",
                "fun": lambda w: np.dot(w, mean_returns) - target,
            }

            result = sco.minimize(
                _portfolio_vol,
                np.ones(n) / n,
                method="SLSQP",
                bounds=bounds,
                constraints=[constraints, target_constraint],
            )

            if result.success:
                vol = _portfolio_vol(result.x)
                frontier.append((round(float(vol), 4), round(float(target), 4)))

        return frontier


if __name__ == "__main__":
    opt = PortfolioOptimizer()
    # Demo: 5 hisse
    result = opt.optimize(symbols=["THYAO", "GARAN", "ASELS", "TUPRS", "KCHOL"])
    print("Optimal Portfoy:")
    for sym, w in result.get("weights", {}).items():
        print(f"  {sym}: %{w*100:.2f}")
    print(f"Sharpe: {result.get('sharpe')}")
    print(f"Beklenen Getiri: {result.get('expected_return')}")
    print(f"Volatilite: {result.get('volatility')}")
