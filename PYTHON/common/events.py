"""
events.py — Event-driven hierarchy for AnatoliaX message bus.
Inspired by Nautilus Trader's MessageBus event model.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum


class EventType(str, Enum):
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_ACCEPTED = "ORDER_ACCEPTED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_PARTIAL = "ORDER_PARTIAL"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_UPDATED = "POSITION_UPDATED"
    POSITION_CLOSED = "POSITION_CLOSED"
    RISK_DENIED = "RISK_DENIED"
    RISK_APPROVED = "RISK_APPROVED"
    KILL_SWITCH_TRIGGERED = "KILL_SWITCH_TRIGGERED"
    MARKET_DATA = "MARKET_DATA"
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    AGENT_DECISION = "AGENT_DECISION"
    # Phase 1-5 enhancement events
    MICROSTRUCTURE_ALERT = "MICROSTRUCTURE_ALERT"
    ORDER_BOOK_UPDATE = "ORDER_BOOK_UPDATE"
    LIQUIDITY_COLLAPSE_WARNING = "LIQUIDITY_COLLAPSE_WARNING"
    TOXIC_FLOW_DETECTED = "TOXIC_FLOW_DETECTED"
    REGIME_TRANSITION = "REGIME_TRANSITION"
    ALPHA_DECAY_ALERT = "ALPHA_DECAY_ALERT"
    STRATEGY_GENOME_MUTATION = "STRATEGY_GENOME_MUTATION"
    RESEARCH_HYPOTHESIS = "RESEARCH_HYPOTHESIS"
    FPGA_SIGNAL = "FPGA_SIGNAL"
    ARBITRAGE_OPPORTUNITY = "ARBITRAGE_OPPORTUNITY"
    RL_ACTION_SELECTED = "RL_ACTION_SELECTED"
    GPU_PIPELINE_COMPLETE = "GPU_PIPELINE_COMPLETE"
    COLOCATION_ALERT = "COLOCATION_ALERT"
    MLOPS_MODEL_APPROVED = "MLOPS_MODEL_APPROVED"
    COMPLIANCE_VIOLATION = "COMPLIANCE_VIOLATION"
    CLUSTER_SCALE_EVENT = "CLUSTER_SCALE_EVENT"


@dataclass
class Event:
    """Base event."""
    event_type: Optional[EventType] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderEvent(Event):
    """Emir gönderildiğinde üretilir."""
    order_id: str = ""
    symbol: str = ""
    side: str = ""  # BUY / SELL
    size: float = 0.0
    price: float = 0.0
    order_type: str = "market"
    sl: Optional[float] = None
    tp: Optional[float] = None
    source: str = "live"

    def __post_init__(self):
        if self.event_type is None:
            self.event_type = EventType.ORDER_SUBMITTED


@dataclass
class FillEvent(Event):
    """Emir dolduğunda/partial dolduğunda üretilir."""
    order_id: str = ""
    filled_size: float = 0.0
    avg_fill_price: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    remaining: float = 0.0

    def __post_init__(self):
        if self.event_type is None:
            self.event_type = EventType.ORDER_FILLED


@dataclass
class PositionEvent(Event):
    """Pozisyon açıldı/güncellendi/kapandı."""
    symbol: str = ""
    quantity: float = 0.0
    avg_price: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    side: str = ""  # long / short

    def __post_init__(self):
        if self.event_type is None:
            self.event_type = EventType.POSITION_UPDATED


@dataclass
class RiskEvent(Event):
    """Risk kontrol sonucu."""
    check_type: str = ""  # kill_switch, exposure, heat, rate_limit
    passed: bool = False
    reason: str = ""
    order_id: Optional[str] = None

    def __post_init__(self):
        if self.event_type is None:
            self.event_type = EventType.RISK_DENIED


@dataclass
class Command:
    """Bus üzerinden gönderilen komut."""
    instruction: str = ""  # PLACE_ORDER, CANCEL_ORDER, SCAN_SIGNALS
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
