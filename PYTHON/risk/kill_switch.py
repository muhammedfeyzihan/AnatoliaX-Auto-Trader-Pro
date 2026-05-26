"""
kill_switch.py — Max drawdown kill switch, circuit breaker, volatility throttling
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Callable, List


class KillSwitch:
    """
    Canli piyasada kritik risk limiti asildiginda tum emirleri durdurur.
    - Max drawdown limiti
    - Gunluk kayip limiti
    - Arka arkaya N zararli islem
    - Manuel kill switch
    """

    def __init__(
        self,
        max_drawdown_pct: float = 0.10,
        daily_loss_pct: float = 0.03,
        consecutive_losses: int = 5,
        on_trigger: Optional[Callable] = None,
    ):
        self.max_drawdown_pct = max_drawdown_pct
        self.daily_loss_pct = daily_loss_pct
        self.consecutive_losses = consecutive_losses
        self.on_trigger = on_trigger
        self._armed = True
        self._triggered = False
        self._trigger_reason = ""
        self._loss_streak = 0
        self._daily_pnl = 0.0
        self._peak = 0.0
        self._alerts: List[str] = []

    def update(self, capital: float, daily_pnl: float, last_trade_pnl: float = 0.0):
        if not self._armed or self._triggered:
            return

        self._daily_pnl = daily_pnl
        if capital > self._peak:
            self._peak = capital

        dd = (self._peak - capital) / self._peak if self._peak > 0 else 0.0

        if dd >= self.max_drawdown_pct:
            self._trigger(f"Max Drawdown: %{dd*100:.2f} >= %{self.max_drawdown_pct*100}")
            return

        if daily_pnl < -self.daily_loss_pct * capital:
            self._trigger(f"Daily Loss: {daily_pnl:.2f} < {-self.daily_loss_pct*capital:.2f}")
            return

        if last_trade_pnl < 0:
            self._loss_streak += 1
        else:
            self._loss_streak = 0

        if self._loss_streak >= self.consecutive_losses:
            self._trigger(f"Consecutive Losses: {self._loss_streak}")
            return

    def _trigger(self, reason: str):
        self._triggered = True
        self._trigger_reason = reason
        self._alerts.append(f"KILL_SWITCH [{datetime.now(timezone.utc).isoformat()}]: {reason}")
        if self.on_trigger:
            self.on_trigger(reason)

    def is_alive(self) -> bool:
        return not self._triggered

    def disarm(self):
        self._armed = False

    def reset(self):
        self._triggered = False
        self._armed = True
        self._loss_streak = 0
        self._daily_pnl = 0.0
        self._alerts.clear()

    def get_alerts(self) -> List[str]:
        return self._alerts.copy()


class CircuitBreaker:
    """Basit circuit breaker: hata sayisi limitine ulasinca acilir."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout_sec: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self._failures = 0
        self._last_failure = None
        self._open = False

    def call(self, fn, *args, **kwargs):
        if self._open:
            if self._last_failure and (datetime.now(timezone.utc) - self._last_failure).total_seconds() > self.recovery_timeout_sec:
                self._open = False
                self._failures = 0
            else:
                raise RuntimeError("Circuit breaker OPEN")

        try:
            result = fn(*args, **kwargs)
            self._failures = 0
            return result
        except Exception as e:
            self._failures += 1
            self._last_failure = datetime.now(timezone.utc)
            if self._failures >= self.failure_threshold:
                self._open = True
            raise

    def is_open(self) -> bool:
        if self._open and self._last_failure:
            if (datetime.now(timezone.utc) - self._last_failure).total_seconds() > self.recovery_timeout_sec:
                self._open = False
                self._failures = 0
        return self._open
