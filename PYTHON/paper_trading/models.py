"""
Paper Trading modelleri
Sanal emir, pozisyon ve sinyal kayitlari.

Mevcut risk.models Base'ini kullanir (database.py init_db tum tablolari olusturur).
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Text
from datetime import datetime, timezone
from risk.models import Base


class PaperTrade(Base):
    __tablename__ = "paper_trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # BUY / SELL
    size = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    stop_loss = Column(Float)
    take_profit_1 = Column(Float)
    take_profit_2 = Column(Float)
    status = Column(String(20), default="OPEN")  # OPEN / CLOSED / CANCELLED
    open_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    close_time = Column(DateTime)
    commission = Column(Float, default=0.0)
    slippage = Column(Float, default=0.0)
    bsmv = Column(Float, default=0.0)
    gross_pnl = Column(Float, default=0.0)
    net_pnl = Column(Float, default=0.0)
    strategy = Column(String(50), default="")
    agent = Column(String(10), default="")
    signal_id = Column(Integer, default=None)
    notes = Column(Text, default="")

    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "side": self.side,
            "size": self.size,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "status": self.status,
            "open_time": self.open_time.isoformat() if self.open_time else None,
            "close_time": self.close_time.isoformat() if self.close_time else None,
            "commission": self.commission,
            "slippage": self.slippage,
            "bsmv": self.bsmv,
            "net_pnl": self.net_pnl,
            "strategy": self.strategy,
            "agent": self.agent,
        }


class PaperPortfolio(Base):
    __tablename__ = "paper_portfolio"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), nullable=False, unique=True, index=True)  # YYYY-MM-DD
    cash = Column(Float, nullable=False, default=100000.0)
    total_value = Column(Float, nullable=False)
    open_positions_count = Column(Integer, default=0)
    daily_pnl = Column(Float, default=0.0)
    cumulative_pnl = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    total_trades_today = Column(Integer, default=0)
    regime = Column(String(20), default="")
    notes = Column(Text, default="")


class PaperSignal(Base):
    __tablename__ = "paper_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    signal_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    strategy = Column(String(50), default="")
    entry_price = Column(Float)
    sl_price = Column(Float)
    tp1_price = Column(Float)
    tp2_price = Column(Float)
    r_r = Column(Float)
    kelly = Column(Float)
    mirofish = Column(Float)
    signal_score = Column(Float)
    regime = Column(String(20), default="")
    macro_score = Column(Float)
    news_sentiment = Column(Float)
    outcome = Column(String(20), default="PENDING")  # PENDING / FILLED / REJECTED / EXPIRED
    fill_price = Column(Float)
    close_price = Column(Float)
    realized_pnl = Column(Float)
    notes = Column(Text, default="")
