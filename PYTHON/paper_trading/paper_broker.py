"""
AnatoliaX Paper Broker
Sanal emir, pozisyon ve P&L yonetimi.

Kullanim:
    from paper_trading.paper_broker import PaperBroker
    broker = PaperBroker(initial_capital=100000)
    broker.place_order("THYAO", "BUY", 100, 103.0, sl=99.0, tp1=110.0, tp2=115.0)
    broker.close_trade(1, 110.0)
    summary = broker.get_portfolio_summary()

Not: .env'de AX_PAPER_TRADING=true olmali.
"""

import os
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

from datetime import datetime, timezone
from typing import Literal

from risk.database import get_session
from paper_trading.models import PaperTrade, PaperPortfolio
from backtest.commission import CommissionModel
from backtest.slippage import SlippageModel


class PaperBroker:
    """
    Sanal broker: Emir alir, pozisyon tutar, P&L hesaplar.
    Komisyon + BSMV + slippage dahil net kar hesaplar.
    """

    def __init__(
        self,
        initial_capital: float | None = None,
        commission_rate: float = 0.001,
        bsmv_rate: float = 0.001,
        max_positions: int | None = None,
        max_risk_pct: float | None = None,
    ):
        self.initial_capital = initial_capital or float(
            os.getenv("AX_PAPER_INITIAL_CAPITAL", 100000)
        )
        self.commission = CommissionModel(commission_rate=commission_rate, bsmv_rate=bsmv_rate)
        self.slippage = SlippageModel(base_rate=0.001, max_rate=0.01)
        self.max_positions = max_positions or int(os.getenv("AX_PAPER_MAX_POSITIONS", 5))
        self.max_risk_pct = max_risk_pct or float(os.getenv("AX_PAPER_MAX_RISK_PCT", 10.0))
        self._ensure_portfolio_record()

    def _ensure_portfolio_record(self):
        """Bugune ait PaperPortfolio kaydi yoksa olustur."""
        session = get_session()
        today = datetime.now().strftime("%Y-%m-%d")
        record = session.query(PaperPortfolio).filter_by(date=today).first()
        if record is None:
            record = PaperPortfolio(
                date=today,
                cash=self.initial_capital,
                total_value=self.initial_capital,
                open_positions_count=0,
                daily_pnl=0.0,
                cumulative_pnl=0.0,
            )
            session.add(record)
            session.commit()
        session.close()

    def _get_db_session(self):
        return get_session()

    def place_order(
        self,
        symbol: str,
        side: Literal["BUY", "SELL"],
        size: float,
        price: float,
        sl: float | None = None,
        tp1: float | None = None,
        tp2: float | None = None,
        strategy: str = "",
        agent: str = "A",
        signal_id: int | None = None,
    ) -> PaperTrade | None:
        """
        Sanal emir ver. Risk limitlerini kontrol et.
        Returns: PaperTrade objesi veya None (limit asimi)
        """
        session = self._get_db_session()

        # Max pozisyon limiti
        open_count = (
            session.query(PaperTrade)
            .filter_by(status="OPEN")
            .count()
        )
        if open_count >= self.max_positions:
            session.close()
            print(f"UYARI: Max pozisyon limiti ({self.max_positions}) asildi. Emir RED.")
            return None

        # Slippage hesapla
        order_value = price * size
        filled_price = self.slippage.apply(price, side, order_value, 500000)
        slip_rate = (filled_price / price) - 1.0 if side == "BUY" else 1.0 - (filled_price / price)
        slip_cost = order_value * slip_rate

        # Komisyon hesapla (emir aninda sadece giris komisyonu)
        comm = self.commission.commission_rate * order_value
        bsmv = self.commission.bsmv_rate * order_value

        trade = PaperTrade(
            symbol=symbol.upper(),
            side=side,
            size=size,
            entry_price=filled_price,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            status="OPEN",
            commission=comm,
            slippage=slip_cost,
            bsmv=bsmv,
            strategy=strategy,
            agent=agent,
            signal_id=signal_id,
            notes=f"Emir verildi. Slippage: {slip_rate:.4f}",
        )

        session.add(trade)
        session.commit()
        trade_id = trade.id
        session.close()

        print(
            f"[PAPER] {side} {size} {symbol} @ {filled_price:.2f} "
            f"(Komisyon: {comm:.2f}, BSMV: {bsmv:.2f}, Slip: {slip_cost:.2f})"
        )

        # Yeni session ile geri dondur
        session = self._get_db_session()
        trade = session.query(PaperTrade).filter_by(id=trade_id).first()
        return trade

    def close_trade(
        self,
        trade_id: int,
        exit_price: float,
        reason: str = "manual",
    ) -> PaperTrade | None:
        """
        Pozisyonu kapat. Net P&L hesapla (komisyon + BSMV + slippage dahil).
        """
        session = self._get_db_session()
        trade = session.query(PaperTrade).filter_by(id=trade_id, status="OPEN").first()
        if trade is None:
            session.close()
            print(f"UYARI: Acik trade bulunamadi (ID: {trade_id})")
            return None

        # Cikis slippage
        order_value = exit_price * trade.size
        close_side = "SELL" if trade.side == "BUY" else "BUY"
        filled_exit = self.slippage.apply(exit_price, close_side, order_value, 500000)
        slip_rate = self.slippage.calculate(order_value, avg_daily_volume=500000, price=exit_price)
        slip_cost = order_value * slip_rate

        # Cikis komisyonu
        exit_comm = self.commission.commission_rate * order_value
        exit_bsmv = self.commission.bsmv_rate * order_value

        # Brut P&L
        if trade.side == "BUY":
            gross = (filled_exit - trade.entry_price) * trade.size
        else:
            gross = (trade.entry_price - filled_exit) * trade.size

        # Toplam maliyet
        total_cost = (
            trade.commission + trade.bsmv + trade.slippage +
            exit_comm + exit_bsmv + slip_cost
        )

        net = gross - total_cost

        trade.exit_price = filled_exit
        trade.status = "CLOSED"
        trade.close_time = datetime.now(timezone.utc)
        trade.gross_pnl = gross
        trade.net_pnl = net
        trade.notes = f"{trade.notes} | Kapatma: {reason} | Net P&L: {net:.2f}"

        session.commit()
        session.refresh(trade)
        session.expunge(trade)
        session.close()

        print(
            f"[PAPER] Trade #{trade_id} kapandi. Brut: {gross:.2f}, Net: {net:.2f} "
            f"(Maliyet: {total_cost:.2f})"
        )
        return trade

    def get_open_positions(self) -> list[PaperTrade]:
        """Acik pozisyonlar listesi."""
        session = self._get_db_session()
        trades = (
            session.query(PaperTrade)
            .filter_by(status="OPEN")
            .order_by(PaperTrade.open_time.desc())
            .all()
        )
        session.close()
        return trades

    def get_portfolio_summary(self) -> dict:
        """Portfoy ozeti."""
        session = self._get_db_session()
        today = datetime.now().strftime("%Y-%m-%d")
        portfolio = session.query(PaperPortfolio).filter_by(date=today).first()

        open_trades = self.get_open_positions()
        open_count = len(open_trades)

        # Gunluk P&L
        today_trades = (
            session.query(PaperTrade)
            .filter(
                PaperTrade.status == "CLOSED",
                PaperTrade.close_time >= datetime.strptime(today, "%Y-%m-%d"),
            )
            .all()
        )
        daily_pnl = sum(t.net_pnl or 0 for t in today_trades)

        # Alarm kontrolu
        alerts = []
        if daily_pnl < -self.initial_capital * (self.max_risk_pct / 100):
            alerts.append(f"Gunluk kayip limiti asildi: {daily_pnl:.2f} TL")
        if open_count >= self.max_positions:
            alerts.append(f"Max pozisyon limitine ulasildi: {open_count}")

        session.close()

        return {
            "date": today,
            "cash": portfolio.cash if portfolio else self.initial_capital,
            "total_value": portfolio.total_value if portfolio else self.initial_capital,
            "open_positions": open_count,
            "daily_pnl": daily_pnl,
            "cumulative_pnl": portfolio.cumulative_pnl if portfolio else 0.0,
            "max_drawdown": portfolio.max_drawdown if portfolio else 0.0,
            "alerts": alerts,
        }

    def get_daily_pnl(self) -> float:
        """Bugunku toplam net P&L."""
        session = self._get_db_session()
        today = datetime.now().strftime("%Y-%m-%d")
        trades = (
            session.query(PaperTrade)
            .filter(
                PaperTrade.status == "CLOSED",
                PaperTrade.close_time >= datetime.strptime(today, "%Y-%m-%d"),
            )
            .all()
        )
        total = sum(t.net_pnl or 0 for t in trades)
        session.close()
        return total


if __name__ == "__main__":
    broker = PaperBroker()
    trade = broker.place_order("THYAO", "BUY", 100, 103.0, sl=99.0, tp1=110.0, tp2=115.0)
    if trade:
        broker.close_trade(trade.id, 110.0, reason="TP1")
    print(broker.get_portfolio_summary())
