"""
rl/agent.py — DQN / PPO ajan implementasyonu
"""
from typing import Dict


class RLAgent:
    """
    Basit DQN ajan stub.

    Ag:
    - Input: gozlem vektoru
    - Hidden: 2 katman
    - Output: Q-value (HOLD, BUY, SELL)

    K199: RL ajan egitimi backtest verisi uzerinden yapilir; canliya gecmeden 100+ episode gerekir.
    """

    def __init__(self, state_dim: int, action_dim: int = 3):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self._network = None

    def act(self, state: Dict) -> int:
        # Placeholder: rastgele eylem
        import random
        return random.randint(0, self.action_dim - 1)

    def train(self, env, episodes: int = 100) -> None:
        for _ in range(episodes):
            env.reset()
            done = False
            while not done:
                action = self.act(env._observe())
                env.step(action)
