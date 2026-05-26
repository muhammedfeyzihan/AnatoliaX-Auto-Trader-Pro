"""
options/greeks.py — Opsiyon Greek'leri hesabi
"""
from decimal import Decimal
from math import exp, log, sqrt
from typing import Dict


class GreeksCalculator:
    """
    Black-Scholes Greek hesaplayici.

    Greek'ler:
    - Delta: fiyat hassasiyeti
    - Gamma: delta degisim hizi
    - Theta: zaman kaybi
    - Vega: oynaklik hassasiyeti
    - Rho: faiz hassasiyeti

    K202: Opsiyon Greek'leri VIOP opsiyonlari icin uygulanir.
    """

    @staticmethod
    def d1(S, K, T, r, sigma) -> float:
        return (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))

    @staticmethod
    def d2(S, K, T, r, sigma) -> float:
        return GreeksCalculator.d1(S, K, T, r, sigma) - sigma * sqrt(T)

    def calculate(self, S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call") -> Dict:
        from math import erf, pi
        d1 = self.d1(S, K, T, r, sigma)
        d2 = self.d2(S, K, T, r, sigma)
        nd1 = 0.5 * (1 + erf(d1 / sqrt(2)))
        nd2 = 0.5 * (1 + erf(d2 / sqrt(2)))
        delta = nd1 if option_type == "call" else nd1 - 1
        gamma = (1 / sqrt(2 * pi)) * exp(-0.5 * d1 ** 2) / (S * sigma * sqrt(T))
        return {"delta": delta, "gamma": gamma, "d1": d1, "d2": d2}
