"""
rl/environment.py — Trading ortami (Gymnasium tarzi)
"""
from typing import Tuple, Dict


class TradingEnvironment:
    """
    Tek hisse RL ortami.

    Gozlem uzayi:
    - Fiyat (OHLCV)
    - Teknik gostergeler (EMA, RSI, MACD)
    - Makro ozellikler

    Eylem uzayi:
    - 0: Tut (HOLD)
    - 1: Al (BUY)
    - 2: Sat (SELL)

    Odul:
    - Sharpe ratio bazli + drawdown cezasi

    K198: RL ortami backtest motoru ile senkronize calisir.
    """

    def __init__(self, data, initial_cash: float = 100000.0):
        self.data = data
        self.initial_cash = initial_cash
        self.reset()

    def reset(self) -> Dict:
        self.step_idx = 0
        self.cash = self.initial_cash
        self.position = 0
        return self._observe()

    def step(self, action: int) -> Tuple[Dict, float, bool, Dict]:
        price = self.data[self.step_idx]["close"]
        reward = 0.0
        if action == 1 and self.cash >= price:
            self.position += 1
            self.cash -= price
        elif action == 2 and self.position > 0:
            self.position -= 1
            self.cash += price
        self.step_idx += 1
        done = self.step_idx >= len(self.data)
        obs = self._observe()
        return obs, reward, done, {}

    def _observe(self) -> Dict:
        row = self.data[self.step_idx]
        return {
            "price": row["close"],
            "cash": self.cash,
            "position": self.position,
        }
