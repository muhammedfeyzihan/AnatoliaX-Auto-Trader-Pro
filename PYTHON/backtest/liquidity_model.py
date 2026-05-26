"""
liquidity_model.py — Derinlik/Liquidity Model (K135)
"""


class LiquidityModel:
    """
    Emir derinligi tahmini ve likidite kontrolu.
    """

    def __init__(self, min_depth: float = 100000, depth_factor: float = 0.01):
        self.min_depth = min_depth
        self.depth_factor = depth_factor

    def estimate_depth(self, avg_volume: float, bid_ask_spread: float) -> dict:
        spread_pct = bid_ask_spread * 100 if bid_ask_spread > 0 else 0.001
        depth = avg_volume * self.depth_factor / spread_pct
        return {
            "depth": depth,
            "adequate": depth >= self.min_depth,
            "spread": bid_ask_spread,
        }

    def can_fill(self, order_value: float, avg_volume: float, bid_ask_spread: float) -> bool:
        info = self.estimate_depth(avg_volume, bid_ask_spread)
        return info["adequate"] and order_value <= info["depth"] * 0.1
