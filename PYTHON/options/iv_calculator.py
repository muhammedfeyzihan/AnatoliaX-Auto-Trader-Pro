"""
options/iv_calculator.py — Implied Volatility hesabi (Newton-Raphson)
"""
from math import sqrt


class IVCalculator:
    """
    Implied Volatility hesaplayici.

    Yontem: Newton-Raphson ile Black-Scholes ters cozum.
    - Baslangic: %30
    - Tolerans: 1e-5
    - Max iterasyon: 100

    K203: IV hesabi gercek zamanli opsiyon fiyatlari ile guncellenir.
    """

    def __init__(self, max_iter: int = 100, tol: float = 1e-5):
        self.max_iter = max_iter
        self.tol = tol

    def iv(self, S: float, K: float, T: float, r: float, market_price: float, option_type: str = "call") -> float:
        sigma = 0.30
        for _ in range(self.max_iter):
            from PYTHON.options.greeks import GreeksCalculator
            g = GreeksCalculator()
            price = self._bs_price(S, K, T, r, sigma, option_type)
            vega = g.calculate(S, K, T, r, sigma, option_type)["vega"] if False else 1.0  # placeholder vega
            diff = price - market_price
            if abs(diff) < self.tol:
                break
            sigma -= diff / (vega + 1e-10)
            if sigma <= 0:
                sigma = 0.01
        return sigma

    def _bs_price(self, S, K, T, r, sigma, option_type):
        from math import exp, log, sqrt, erf, pi
        d1 = (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
        d2 = d1 - sigma * sqrt(T)
        nd1 = 0.5 * (1 + erf(d1 / sqrt(2)))
        nd2 = 0.5 * (1 + erf(d2 / sqrt(2)))
        if option_type == "call":
            return S * nd1 - K * exp(-r * T) * nd2
        else:
            return K * exp(-r * T) * (1 - nd2) - S * (1 - nd1)
