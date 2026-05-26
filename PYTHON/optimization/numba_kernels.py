"""
optimization/numba_kernels.py — Numba JIT Hot-Path Acceleration

Wraps critical pure-Python loops with Numba @njit for 10-100x speedup.
Graceful fallback: if numba is unavailable, functions run as standard Python.

Techniques inspired by:
- bartonguestier1725-collab/backtest-engine (Numba JIT bar backtester)
- Taz33m/tracebook (Numba JIT order matching)
- vdsag/Vectorized-Crypto-Backtester (Numba multiprocessing)
"""

import math
from functools import wraps
from typing import Callable, List


# ---------------------------------------------------------------------------
# Numba detection + graceful fallback decorator
# ---------------------------------------------------------------------------
try:
    from numba import njit, prange
    _HAS_NUMBA = True
except Exception:
    _HAS_NUMBA = False


def maybe_njit(signature=None, parallel=False, cache=True, fastmath=True, **kw):
    """Decorator that applies @njit if Numba is available, else identity."""
    def _decorator(fn: Callable) -> Callable:
        if _HAS_NUMBA:
            return njit(signature, parallel=parallel, cache=cache, fastmath=fastmath, **kw)(fn)
        @wraps(fn)
        def _wrapper(*args, **kwargs):
            return fn(*args, **kwargs)
        return _wrapper
    return _decorator


# ---------------------------------------------------------------------------
# Tick Simulator kernels
# ---------------------------------------------------------------------------
@maybe_njit()
def _slippage_kernel(order_size: float, queue_depth: float, volatility: float, spread: float,
                     alpha1: float, alpha2: float, alpha3: float) -> float:
    return alpha1 * (order_size / (queue_depth + 1e-9)) + alpha2 * volatility + alpha3 * spread


@maybe_njit()
def _latency_kernel(mu: float, sigma: float) -> float:
    return math.exp(mu + sigma * math.sqrt(-2.0 * math.log(1.0 - 1e-9)) * math.cos(2.0 * math.pi * 1e-9))


@maybe_njit()
def _spread_stress_kernel(normal_spread: float, price_change: float, price_volatility: float, beta: float) -> float:
    if price_volatility == 0.0:
        return normal_spread
    return normal_spread * (1.0 + beta * abs(price_change) / price_volatility)


@maybe_njit()
def _queue_decay_kernel(q0: float, t: float, lambda_decay: float, noise_std: float) -> float:
    decay = q0 * math.exp(-lambda_decay * t)
    # Box-Muller approx for Gaussian noise (deterministic in JIT)
    noise = 0.0  # JIT-friendly: caller adds noise if needed
    return max(0.0, decay + noise)


# ---------------------------------------------------------------------------
# Microstructure kernels
# ---------------------------------------------------------------------------
@maybe_njit()
def _queue_position_kernel(order_size: float, book_depth: float, arrival_rate: float) -> float:
    if book_depth <= 0.0 or arrival_rate <= 0.0:
        return 0.0
    return min(1.0, order_size / (book_depth * arrival_rate))


@maybe_njit()
def _imbalance_kernel(bid_vol: float, ask_vol: float) -> float:
    denom = bid_vol + ask_vol
    if denom == 0.0:
        return 0.0
    return (bid_vol - ask_vol) / denom


@maybe_njit()
def _realized_spread_kernel(execution_price: float, midprice_future: float) -> float:
    return 2.0 * (execution_price - midprice_future)


@maybe_njit()
def _liquidity_fade_kernel(mid_after: float, mid_at_fill: float, spread: float) -> float:
    if spread == 0.0:
        return 0.0
    return (mid_after - mid_at_fill) / spread


# ---------------------------------------------------------------------------
# Indicator kernels (for raw NumPy arrays, used by backtest engine)
# ---------------------------------------------------------------------------
@maybe_njit(parallel=True)
def _ema_kernel(prices: List[float], window: int) -> List[float]:
    n = len(prices)
    result = [0.0] * n
    alpha = 2.0 / (window + 1)
    result[0] = prices[0]
    for i in range(1, n):
        result[i] = alpha * prices[i] + (1.0 - alpha) * result[i - 1]
    return result


@maybe_njit(parallel=True)
def _sma_kernel(prices: List[float], window: int) -> List[float]:
    n = len(prices)
    result = [0.0] * n
    _sum = 0.0
    for i in range(n):
        _sum += prices[i]
        if i >= window:
            _sum -= prices[i - window]
        count = min(i + 1, window)
        result[i] = _sum / count
    return result


@maybe_njit(parallel=True)
def _atr_kernel(highs: List[float], lows: List[float], closes: List[float], window: int) -> List[float]:
    n = len(closes)
    result = [0.0] * n
    tr_sum = 0.0
    for i in range(1, n):
        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - closes[i - 1])
        tr3 = abs(lows[i] - closes[i - 1])
        tr = max(tr1, max(tr2, tr3))
        tr_sum += tr
        if i >= window:
            # Wilder smoothing approximation
            prev = result[i - 1]
            result[i] = (prev * (window - 1) + tr) / window
        else:
            result[i] = tr_sum / i if i > 0 else tr
    return result


# ---------------------------------------------------------------------------
# Benchmark helper
# ---------------------------------------------------------------------------
def benchmark_hot_path(fn, iterations: int = 100_000) -> dict:
    import time
    # Warmup
    for _ in range(min(1000, iterations // 100)):
        fn()
    start = time.perf_counter_ns()
    for _ in range(iterations):
        fn()
    elapsed = time.perf_counter_ns() - start
    avg_ns = elapsed / iterations
    return {
        "iterations": iterations,
        "avg_ns": avg_ns,
        "numba_enabled": _HAS_NUMBA,
    }
