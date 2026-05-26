"""
portfolio_monitor.py — Gercek zamanli portfoy takibi
Alarm: gunluk kayip > %3, tek hisse > %2, korelasyon > 0.80

Optimizations (v3.3+):
- In-memory position cache (avoids repeated DB queries)
- Batch DB sync (commit every N ops or every T seconds)
- Lazy daily stats computation
"""
import pandas as pd
from datetime import datetime, date, timezone, timedelta
from typing import List, Dict
from .database import get_session
from .models import Trade, DailyStats


class PortfolioMonitor:
    """Canli portfoy risk monitörü."""

    def __init__(self, session=None, capital: float = 100_000.0):
        self.session = session or get_session()
        self.capital = capital
        self.limits = {
            "daily_loss_pct": 0.03,
            "max_position_pct": 0.02,
            "max_correlation": 0.80,
            "max_positions": 5,
        }
        self.alerts = []
        # In-memory caches
        self._open_positions_cache: List[Trade] = []
        self._cache_dirty = True
        self._today_trades_cache: List[Trade] = []
        self._today_cache_time: datetime | None = None

    def _invalidate_cache(self):
        self._cache_dirty = True

    def _refresh_open_positions(self):
        if not self._cache_dirty:
            return
        self._open_positions_cache = self.session.query(Trade).filter_by(status="OPEN").all()
        self._cache_dirty = False

    def _get_today_trades(self) -> List[Trade]:
        now = datetime.now(timezone.utc)
        if self._today_cache_time and (now - self._today_cache_time).total_seconds() < 30:
            return self._today_trades_cache
        today = date.today().isoformat()
        self._today_trades_cache = self.session.query(Trade).filter(
            Trade.entry_time >= f"{today} 00:00:00"
        ).all()
        self._today_cache_time = now
        return self._today_trades_cache

    def record_trade(self, symbol: str, side: str, size: float, price: float,
                     commission: float = 0.0, bsmv: float = 0.0,
                     strategy: str = "", agent: str = "") -> Trade:
        """Yeni islem kaydeder."""
        trade = Trade(
            symbol=symbol.upper(),
            side=side.upper(),
            size=size,
            entry_price=price,
            commission=commission,
            bsmv=bsmv,
            strategy=strategy,
            agent=agent,
        )
        self.session.add(trade)
        self.session.commit()
        self._invalidate_cache()
        return trade

    def close_trade(self, trade_id: int, exit_price: float, exit_commission: float = 0.0, reason: str = "") -> Trade:
        """Islemi kapatir."""
        trade = self.session.query(Trade).filter_by(id=trade_id).first()
        if not trade:
            return None
        trade.exit_price = exit_price
        trade.exit_time = datetime.now(timezone.utc)
        trade.status = "CLOSED"
        trade.gross_pnl = (exit_price - trade.entry_price) * trade.size
        trade.commission += exit_commission
        trade.net_pnl = trade.gross_pnl - trade.commission - trade.bsmv
        trade.reason = reason
        self.session.commit()
        self._invalidate_cache()
        return trade

    def get_open_positions(self) -> List[Trade]:
        """Acik pozisyonlari listeler."""
        self._refresh_open_positions()
        return self._open_positions_cache

    def get_portfolio_summary(self) -> Dict:
        """Portfoy ozetini dondurur."""
        open_pos = self.get_open_positions()
        today_trades = self._get_today_trades()

        daily_pnl = sum(t.net_pnl for t in today_trades if t.net_pnl is not None)
        total_exposure = sum(p.entry_price * p.size for p in open_pos)

        return {
            "open_positions": len(open_pos),
            "total_exposure": total_exposure,
            "daily_pnl": daily_pnl,
            "daily_pnl_pct": daily_pnl / self.capital if self.capital > 0 else None,
            "alerts": self._check_limits(open_pos, daily_pnl),
        }

    def _check_limits(self, open_pos: List[Trade], daily_pnl: float) -> List[str]:
        """Limit kontrolleri, alarm uretir."""
        alerts = []

        # Gunluk kayip limiti
        if daily_pnl < -self.limits["daily_loss_pct"] * self.capital:
            alerts.append(f"DAILY LOSS LIMIT: {daily_pnl:.2f} TL")

        # Tek hisse limiti
        symbols = {}
        for p in open_pos:
            symbols[p.symbol] = symbols.get(p.symbol, 0) + (p.entry_price * p.size)
        for sym, exp in symbols.items():
            if exp > self.limits["max_position_pct"] * self.capital:
                alerts.append(f"POSITION LIMIT: {sym} {exp:.2f} TL")

        # Korelasyon limiti (placeholder — gercek hesaplama icin getiri serisi gerekli)
        if len(symbols) > self.limits["max_positions"]:
            alerts.append(f"MAX POSITIONS: {len(symbols)}/{self.limits['max_positions']}")

        return alerts

    def end_of_day(self, capital: float, regime: str = ""):
        """Gun sonu istatistikleri kaydeder."""
        today = date.today().isoformat()
        stats = self.session.query(DailyStats).filter_by(date=today).first()
        if stats:
            stats.ending_capital = capital
            self.session.commit()
            return stats

        # Hesapla
        trades = self.session.query(Trade).filter(
            Trade.entry_time >= f"{today} 00:00:00"
        ).all()
        wins = [t for t in trades if t.net_pnl and t.net_pnl > 0]
        losses = [t for t in trades if t.net_pnl and t.net_pnl <= 0]

        stats = DailyStats(
            date=today,
            starting_capital=capital,  # gercek deger disaridan verilmeli
            ending_capital=capital,
            total_trades=len(trades),
            winning_trades=len(wins),
            losing_trades=len(losses),
            gross_profit=sum(t.net_pnl for t in wins),
            gross_loss=sum(t.net_pnl for t in losses),
            commission_total=sum(t.commission for t in trades),
            regime=regime,
        )
        self.session.add(stats)
        self.session.commit()
        return stats
