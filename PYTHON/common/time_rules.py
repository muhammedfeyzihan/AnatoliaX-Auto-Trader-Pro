"""
time_rules.py — Zaman Bazli Trading Kurallari ve Uyari Sistemi (K246-K248)

Optimal trading pencereleri, zaman bazli risk ayarlari, ogle arasi kacinma,
pre-market/post-market analiz, EOD pozisyon kapatma, ve zaman bazli uyari motoru.

Integration: SignalEngine, main.py, BISTCalendar
"""

from datetime import datetime, time, timedelta, timezone
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Callable
from enum import Enum
import threading


class TradingWindow(Enum):
    PRE_MARKET = "pre_market"        # 07:00 - 09:30
    OPENING = "opening"              # 09:30 - 10:00
    MORNING = "morning"              # 10:00 - 11:30
    LUNCH = "lunch"                  # 11:30 - 13:00
    AFTERNOON = "afternoon"          # 13:00 - 15:00
    CLOSING = "closing"              # 15:00 - 18:00
    POST_MARKET = "post_market"      # 18:00 - 23:59
    NIGHT = "night"                  # 00:00 - 07:00


class TimeAlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    BLOCK = "block"


@dataclass
class TimeAlert:
    level: TimeAlertLevel
    message: str
    timestamp: datetime
    window: TradingWindow
    action_required: bool = False


@dataclass
class WindowConfig:
    window: TradingWindow
    start: time
    end: time
    can_trade: bool
    risk_multiplier: float = 1.0
    position_size_multiplier: float = 1.0
    sl_multiplier: float = 1.0
    tp_multiplier: float = 1.0
    max_positions: int = 5
    description: str = ""
    priority: int = 1  # 1 = highest


class TimeBasedTradingManager:
    """
    Zaman bazli trading yonetimi ve uyari motoru.

    Usage:
        tm = TimeBasedTradingManager()
        if tm.can_trade_now():
            config = tm.get_current_window_config()
            risk_adj = config.risk_multiplier
    """

    DEFAULT_WINDOWS: List[WindowConfig] = [
        WindowConfig(
            window=TradingWindow.PRE_MARKET,
            start=time(7, 0), end=time(9, 30),
            can_trade=False,
            risk_multiplier=0.0,
            description="Piyasa kapali, analiz ve hazirlik zamani",
            priority=1,
        ),
        WindowConfig(
            window=TradingWindow.OPENING,
            start=time(9, 30), end=time(10, 0),
            can_trade=True,
            risk_multiplier=1.2,
            position_size_multiplier=1.0,
            sl_multiplier=1.5,
            tp_multiplier=1.2,
            max_positions=3,
            description="Acilis momentumu — yuksek volatilite, genis SL",
            priority=1,
        ),
        WindowConfig(
            window=TradingWindow.MORNING,
            start=time(10, 0), end=time(11, 30),
            can_trade=True,
            risk_multiplier=1.0,
            position_size_multiplier=1.0,
            sl_multiplier=1.0,
            tp_multiplier=1.0,
            max_positions=5,
            description="Optimal trading penceresi — normal risk",
            priority=1,
        ),
        WindowConfig(
            window=TradingWindow.LUNCH,
            start=time(11, 30), end=time(13, 0),
            can_trade=False,
            risk_multiplier=0.5,
            position_size_multiplier=0.5,
            sl_multiplier=1.0,
            tp_multiplier=0.8,
            max_positions=2,
            description="Ogle arasi — dusuk hacim, spread artisi, KACIN",
            priority=3,
        ),
        WindowConfig(
            window=TradingWindow.AFTERNOON,
            start=time(13, 0), end=time(15, 0),
            can_trade=True,
            risk_multiplier=0.9,
            position_size_multiplier=1.0,
            sl_multiplier=1.0,
            tp_multiplier=1.0,
            max_positions=4,
            description="Ogleden sonra — trend devami, normal risk",
            priority=2,
        ),
        WindowConfig(
            window=TradingWindow.CLOSING,
            start=time(15, 0), end=time(18, 0),
            can_trade=True,
            risk_multiplier=0.7,
            position_size_multiplier=0.8,
            sl_multiplier=0.8,
            tp_multiplier=0.8,
            max_positions=2,
            description="Kapanis oncesi — pozisyon kucultme, EOD kapatma",
            priority=3,
        ),
        WindowConfig(
            window=TradingWindow.POST_MARKET,
            start=time(18, 0), end=time(23, 59, 59),
            can_trade=False,
            risk_multiplier=0.0,
            description="Piyasa kapali, gece analizi",
            priority=1,
        ),
        WindowConfig(
            window=TradingWindow.NIGHT,
            start=time(0, 0), end=time(7, 0),
            can_trade=False,
            risk_multiplier=0.0,
            max_positions=0,
            description="Gece — sistem bakimi, veri arsivleme",
            priority=1,
        ),
    ]

    def __init__(self, windows: List[WindowConfig] | None = None):
        self.windows = windows or list(self.DEFAULT_WINDOWS)
        self._alerts: List[TimeAlert] = []
        self._alert_callbacks: List[Callable[[TimeAlert], None]] = []
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Window helpers
    # ------------------------------------------------------------------
    def get_current_window(self, dt: Optional[datetime] = None) -> TradingWindow:
        dt = dt or datetime.now(timezone.utc)
        t = dt.time()
        for w in self.windows:
            # Half-open interval to avoid boundary overlap
            if w.start <= t < w.end:
                return w.window
        # If t exactly equals last window's end (23:59:59 case), check <= for last window
        for w in self.windows:
            if w.start <= t <= w.end:
                return w.window
        return TradingWindow.NIGHT

    def get_window_config(self, window: TradingWindow) -> Optional[WindowConfig]:
        for w in self.windows:
            if w.window == window:
                return w
        return None

    def get_current_window_config(self, dt: Optional[datetime] = None) -> Optional[WindowConfig]:
        return self.get_window_config(self.get_current_window(dt))

    # ------------------------------------------------------------------
    # Trading checks
    # ------------------------------------------------------------------
    def can_trade_now(self, dt: Optional[datetime] = None) -> bool:
        cfg = self.get_current_window_config(dt)
        return cfg.can_trade if cfg else False

    def get_risk_multiplier(self, dt: Optional[datetime] = None) -> float:
        cfg = self.get_current_window_config(dt)
        return cfg.risk_multiplier if cfg else 0.0

    def get_position_size_multiplier(self, dt: Optional[datetime] = None) -> float:
        cfg = self.get_current_window_config(dt)
        return cfg.position_size_multiplier if cfg else 0.0

    def get_sl_multiplier(self, dt: Optional[datetime] = None) -> float:
        cfg = self.get_current_window_config(dt)
        return cfg.sl_multiplier if cfg else 1.0

    def get_tp_multiplier(self, dt: Optional[datetime] = None) -> float:
        cfg = self.get_current_window_config(dt)
        return cfg.tp_multiplier if cfg else 1.0

    def get_max_positions(self, dt: Optional[datetime] = None) -> int:
        cfg = self.get_current_window_config(dt)
        return cfg.max_positions if cfg else 0

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------
    def add_alert_callback(self, cb: Callable[[TimeAlert], None]):
        self._alert_callbacks.append(cb)

    def _emit_alert(self, alert: TimeAlert):
        with self._lock:
            self._alerts.append(alert)
        for cb in self._alert_callbacks:
            try:
                cb(alert)
            except Exception:
                pass

    def check_and_alert(self, dt: Optional[datetime] = None) -> List[TimeAlert]:
        """Mevcut zamana gore uyari uret."""
        dt = dt or datetime.now(timezone.utc)
        cfg = self.get_current_window_config(dt)
        alerts = []

        if not cfg:
            return alerts

        # Piyasa kapali uyari
        if not cfg.can_trade:
            alerts.append(TimeAlert(
                level=TimeAlertLevel.BLOCK,
                message=f"Piyasa kapali: {cfg.description}",
                timestamp=dt,
                window=cfg.window,
                action_required=True,
            ))

        # Ogle arasi uyarisi
        if cfg.window == TradingWindow.LUNCH:
            alerts.append(TimeAlert(
                level=TimeAlertLevel.WARNING,
                message="Ogle arasi: Dusuk hacim, spread artisi. Islem KACIN.",
                timestamp=dt,
                window=cfg.window,
                action_required=False,
            ))

        # Kapanis oncesi uyari
        if cfg.window == TradingWindow.CLOSING:
            alerts.append(TimeAlert(
                level=TimeAlertLevel.WARNING,
                message="Kapanis oncesi: Yeni pozisyon ACMA, mevcut pozisyonlari kucult.",
                timestamp=dt,
                window=cfg.window,
                action_required=True,
            ))

        # Acilis momentum uyari
        if cfg.window == TradingWindow.OPENING:
            alerts.append(TimeAlert(
                level=TimeAlertLevel.INFO,
                message="Acilis momentumu: Yuksek volatilite, SL genisletildi.",
                timestamp=dt,
                window=cfg.window,
                action_required=False,
            ))

        for a in alerts:
            self._emit_alert(a)
        return alerts

    def get_alerts(self, level: Optional[TimeAlertLevel] = None) -> List[TimeAlert]:
        with self._lock:
            if level:
                return [a for a in self._alerts if a.level == level]
            return self._alerts.copy()

    def clear_alerts(self):
        with self._lock:
            self._alerts.clear()

    # ------------------------------------------------------------------
    # Optimal trading time suggestions
    # ------------------------------------------------------------------
    def suggest_optimal_trading_time(self, current_dt: Optional[datetime] = None) -> Dict:
        """
        Su an icin en mantikli islem zamanini onerir.
        Returns: {'can_trade_now': bool, 'next_window': str, 'minutes_until': int, 'reason': str}
        """
        current_dt = current_dt or datetime.now(timezone.utc)
        current_cfg = self.get_current_window_config(current_dt)

        if current_cfg and current_cfg.can_trade:
            return {
                "can_trade_now": True,
                "current_window": current_cfg.window.value,
                "risk_multiplier": current_cfg.risk_multiplier,
                "max_positions": current_cfg.max_positions,
                "reason": current_cfg.description,
                "minutes_until": 0,
                "next_window": None,
            }

        # Sonraki trading penceresini bul
        t = current_dt.time()
        future_windows = [w for w in self.windows if w.start > t and w.can_trade]
        if not future_windows:
            # Ertesi gunun acilisini bekle (opening 09:30)
            next_time = datetime.combine(current_dt.date() + timedelta(days=1), time(9, 30), tzinfo=current_dt.tzinfo)
            now = datetime.combine(current_dt.date(), t, tzinfo=current_dt.tzinfo)
            minutes_until = int((next_time - now).total_seconds() / 60)
            return {
                "can_trade_now": False,
                "current_window": current_cfg.window.value if current_cfg else "night",
                "reason": "Piyasa kapali. Bir sonraki trading yarinki acilisi bekleniyor.",
                "minutes_until": minutes_until,
                "next_window": "opening",
                "next_window_start": time(9, 30).isoformat(),
            }

        next_w = min(future_windows, key=lambda w: w.start)
        now = datetime.combine(current_dt.date(), t, tzinfo=current_dt.tzinfo)
        next_time = datetime.combine(current_dt.date(), next_w.start, tzinfo=current_dt.tzinfo)
        if next_time <= now:
            next_time += timedelta(days=1)
        minutes_until = int((next_time - now).total_seconds() / 60)

        return {
            "can_trade_now": False,
            "current_window": current_cfg.window.value if current_cfg else "night",
            "reason": f"Trading yasak. Bir sonraki pencere: {next_w.description}",
            "minutes_until": minutes_until,
            "next_window": next_w.window.value,
            "next_window_start": next_w.start.isoformat(),
        }

    # ------------------------------------------------------------------
    # EOD position closure
    # ------------------------------------------------------------------
    def should_close_positions(self, dt: Optional[datetime] = None) -> bool:
        """Kapanis oncesinde pozisyonlar kapatilmali mi?"""
        dt = dt or datetime.now(timezone.utc)
        t = dt.time()
        # 15:30'dan sonra yeni pozisyon acma, 17:30'dan sonra kalan pozisyonlari kapat
        return t >= time(17, 30)

    def get_time_until_close(self, dt: Optional[datetime] = None) -> int:
        """Kapanisa kalan dakika."""
        dt = dt or datetime.now(timezone.utc)
        close = datetime.combine(dt.date(), time(18, 0), tzinfo=dt.tzinfo)
        if dt >= close:
            return 0
        return int((close - dt).total_seconds() / 60)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    def get_summary(self, dt: Optional[datetime] = None) -> Dict:
        dt = dt or datetime.now(timezone.utc)
        cfg = self.get_current_window_config(dt)
        suggestion = self.suggest_optimal_trading_time(dt)

        return {
            "current_time": dt.isoformat(),
            "current_window": cfg.window.value if cfg else "unknown",
            "can_trade": cfg.can_trade if cfg else False,
            "risk_multiplier": cfg.risk_multiplier if cfg else 0.0,
            "position_size_multiplier": cfg.position_size_multiplier if cfg else 0.0,
            "sl_multiplier": cfg.sl_multiplier if cfg else 1.0,
            "tp_multiplier": cfg.tp_multiplier if cfg else 1.0,
            "max_positions": cfg.max_positions if cfg else 0,
            "description": cfg.description if cfg else "",
            "minutes_until_close": self.get_time_until_close(dt),
            "should_close_positions": self.should_close_positions(dt),
            "optimal_trading_suggestion": suggestion,
        }
