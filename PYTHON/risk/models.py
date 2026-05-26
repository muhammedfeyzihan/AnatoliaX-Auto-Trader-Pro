"""
models.py — SQLAlchemy modelleri (Trade, Position, DailyStats)
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # BUY / SELL
    size = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    status = Column(String(20), default="OPEN")  # OPEN / CLOSED / CANCELLED
    entry_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    exit_time = Column(DateTime)
    commission = Column(Float, default=0.0)
    bsmv = Column(Float, default=0.0)
    gross_pnl = Column(Float, default=0.0)
    net_pnl = Column(Float, default=0.0)
    strategy = Column(String(50), default="")
    agent = Column(String(10), default="")
    reason = Column(Text, default="")

    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "side": self.side,
            "size": self.size,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "status": self.status,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "commission": self.commission,
            "bsmv": self.bsmv,
            "net_pnl": self.net_pnl,
            "strategy": self.strategy,
            "agent": self.agent,
        }


class DailyStats(Base):
    __tablename__ = "daily_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), nullable=False, unique=True, index=True)  # YYYY-MM-DD
    starting_capital = Column(Float, nullable=False)
    ending_capital = Column(Float, nullable=False)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    gross_profit = Column(Float, default=0.0)
    gross_loss = Column(Float, default=0.0)
    commission_total = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    sharpe = Column(Float)
    sortino = Column(Float)
    regime = Column(String(20), default="")
    note = Column(Text, default="")


class AgentScore(Base):
    __tablename__ = "agent_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent = Column(String(10), nullable=False, index=True)
    date = Column(String(10), nullable=False, index=True)
    predictions = Column(Integer, default=0)
    correct = Column(Integer, default=0)
    score = Column(Float, default=0.0)
