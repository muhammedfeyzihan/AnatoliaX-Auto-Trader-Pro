"""
PYTHON/risk/margin_monitor.py — Real-Time Margin & Liquidation Monitor

CRITICAL COMPONENT #6 from Missing Components PDF

Features:
- Real-time margin tracking across all positions
- Liquidation price calculation
- Margin level monitoring
- Auto-deleveraging triggers
- Margin call alerts
- Exchange margin requirements integration

Problem Statement: "Am I about to be liquidated?"
Without this: System cannot prevent liquidation events
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class MarginLevel(Enum):
    SAFE = "safe"  # > 150%
    WARNING = "warning"  # 120-150%
    CRITICAL = "critical"  # 100-120%
    LIQUIDATION_IMMINENT = "liquidation_imminent"  # < 100%


@dataclass
class PositionMargin:
    """Margin info for single position."""
    symbol: str
    position_size: float
    entry_price: float
    current_price: float
    leverage: float
    margin_used: float
    liquidation_price: float
    unrealized_pnl: float


@dataclass
class MarginSummary:
    """Portfolio margin summary."""
    total_equity: float
    total_margin_used: float
    total_margin_available: float
    margin_level: float  # percentage
    margin_level_status: MarginLevel
    total_unrealized_pnl: float
    liquidation_risk: float  # 0-1 scale
    positions_at_risk: List[str]
    timestamp: datetime


class MarginMonitor:
    """
    Real-Time Margin & Liquidation Monitor.
    
    Monitors:
    - Total margin usage
    - Margin level percentage
    - Liquidation prices for each position
    - Auto-deleveraging triggers
    """
    
    def __init__(self, initial_equity: float = 100000.0):
        self.initial_equity = initial_equity
        self._positions: Dict[str, PositionMargin] = {}
        self._margin_history: List[Dict] = []
        self._alerts: List[Dict] = []
        self._exchange_margin_reqs: Dict[str, float] = {}  # symbol -> margin requirement
        self._auto_deleveraging_enabled: bool = True
        self._deleveraging_threshold: float = 120.0  # Start at 120% margin level
    
    def set_exchange_margin_requirement(self, symbol: str, requirement: float) -> None:
        """Set margin requirement for symbol (e.g., 0.1 for 10%)."""
        self._exchange_margin_reqs[symbol] = requirement
    
    def update_position(self, symbol: str, position_size: float, entry_price: float,
                       current_price: float, leverage: float) -> PositionMargin:
        """Update or create position margin info."""
        margin_req = self._exchange_margin_reqs.get(symbol, 0.1)  # Default 10%
        
        # Calculate margin used
        notional = abs(position_size * entry_price)
        margin_used = notional * margin_req
        
        # Calculate liquidation price (simplified for long positions)
        if position_size > 0:  # Long
            liquidation_price = entry_price * (1 - (1 / leverage) + margin_req)
            unrealized_pnl = (current_price - entry_price) * position_size
        else:  # Short
            liquidation_price = entry_price * (1 + (1 / leverage) - margin_req)
            unrealized_pnl = (entry_price - current_price) * abs(position_size)
        
        pos_margin = PositionMargin(
            symbol=symbol,
            position_size=position_size,
            entry_price=entry_price,
            current_price=current_price,
            leverage=leverage,
            margin_used=margin_used,
            liquidation_price=liquidation_price,
            unrealized_pnl=unrealized_pnl
        )
        
        self._positions[symbol] = pos_margin
        return pos_margin
    
    def remove_position(self, symbol: str) -> None:
        """Remove closed position."""
        if symbol in self._positions:
            del self._positions[symbol]
    
    def get_total_equity(self) -> float:
        """Calculate total equity (initial + unrealized PnL)."""
        total_unrealized = sum(p.unrealized_pnl for p in self._positions.values())
        return self.initial_equity + total_unrealized
    
    def get_total_margin_used(self) -> float:
        """Calculate total margin used across all positions."""
        return sum(p.margin_used for p in self._positions.values())
    
    def get_margin_level(self) -> float:
        """Calculate margin level percentage."""
        equity = self.get_total_equity()
        margin_used = self.get_total_margin_used()
        
        if margin_used == 0:
            return float('inf')
        
        return (equity / margin_used) * 100
    
    def get_margin_level_status(self, margin_level: float) -> MarginLevel:
        """Determine margin level status."""
        if margin_level > 150:
            return MarginLevel.SAFE
        elif margin_level > 120:
            return MarginLevel.WARNING
        elif margin_level > 100:
            return MarginLevel.CRITICAL
        else:
            return MarginLevel.LIQUIDATION_IMMINENT
    
    def get_liquidation_risk(self) -> float:
        """
        Calculate liquidation risk score (0-1).
        
        0 = No risk
        1 = Certain liquidation
        """
        margin_level = self.get_margin_level()
        
        if margin_level > 150:
            return 0.0
        elif margin_level > 120:
            return 0.2
        elif margin_level > 100:
            return 0.5
        else:
            # Below 100%, risk increases exponentially
            return min(1.0, (100 - margin_level) / 50 + 0.5)
    
    def get_positions_at_risk(self) -> List[str]:
        """Get list of positions close to liquidation."""
        at_risk = []
        for symbol, pos in self._positions.items():
            # If current price is within 5% of liquidation price
            if pos.position_size > 0:  # Long
                distance = (pos.current_price - pos.liquidation_price) / pos.current_price
            else:  # Short
                distance = (pos.liquidation_price - pos.current_price) / pos.current_price
            
            if distance < 0.05:  # Within 5%
                at_risk.append(symbol)
        
        return at_risk
    
    def check_auto_deleveraging(self) -> Optional[Dict[str, Any]]:
        """
        Check if auto-deleveraging should trigger.
        
        Returns deleveraging recommendation if needed.
        """
        margin_level = self.get_margin_level()
        
        if margin_level >= self._deleveraging_threshold:
            return None
        
        # Find position to close (lowest PnL or highest risk)
        positions_at_risk = self.get_positions_at_risk()
        
        if positions_at_risk:
            # Close highest risk position
            symbol_to_close = positions_at_risk[0]
        else:
            # Close smallest position
            symbol_to_close = min(
                self._positions.keys(),
                key=lambda s: abs(self._positions[s].margin_used)
            )
        
        return {
            'action': 'deleveraging_required',
            'symbol': symbol_to_close,
            'reason': f'Margin level {margin_level:.1f}% below threshold {self._deleveraging_threshold}%',
            'current_margin_level': margin_level,
            'target_margin_level': self._deleveraging_threshold + 10,
            'timestamp': datetime.now(timezone.utc)
        }
    
    def get_margin_summary(self) -> MarginSummary:
        """Get complete margin summary."""
        equity = self.get_total_equity()
        margin_used = self.get_total_margin_used()
        margin_level = self.get_margin_level()
        
        return MarginSummary(
            total_equity=equity,
            total_margin_used=margin_used,
            total_margin_available=equity - margin_used,
            margin_level=margin_level,
            margin_level_status=self.get_margin_level_status(margin_level),
            total_unrealized_pnl=sum(p.unrealized_pnl for p in self._positions.values()),
            liquidation_risk=self.get_liquidation_risk(),
            positions_at_risk=self.get_positions_at_risk(),
            timestamp=datetime.now(timezone.utc)
        )
    
    def record_margin_snapshot(self) -> None:
        """Record margin snapshot for history."""
        summary = self.get_margin_summary()
        snapshot = {
            'timestamp': summary.timestamp.isoformat(),
            'total_equity': summary.total_equity,
            'margin_used': summary.total_margin_used,
            'margin_level': summary.margin_level,
            'margin_level_status': summary.margin_level_status.value,
            'liquidation_risk': summary.liquidation_risk
        }
        self._margin_history.append(snapshot)
        
        # Keep last 10000 snapshots
        if len(self._margin_history) > 10000:
            self._margin_history = self._margin_history[-10000:]
    
    def add_alert(self, alert_type: str, message: str, 
                  severity: str = 'warning') -> None:
        """Add margin alert."""
        alert = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': alert_type,
            'message': message,
            'severity': severity
        }
        self._alerts.append(alert)
        
        # Keep last 1000 alerts
        if len(self._alerts) > 1000:
            self._alerts = self._alerts[-1000:]
    
    def check_and_alert(self) -> List[Dict]:
        """Check margin levels and generate alerts."""
        new_alerts = []
        summary = self.get_margin_summary()
        
        # Record snapshot
        self.record_margin_snapshot()
        
        # Check margin level
        if summary.margin_level_status == MarginLevel.LIQUIDATION_IMMINENT:
            alert = {
                'type': 'LIQUIDATION_WARNING',
                'message': f'CRITICAL: Margin level at {summary.margin_level:.1f}%. Liquidation imminent!',
                'severity': 'critical'
            }
            self.add_alert(alert['type'], alert['message'], alert['severity'])
            new_alerts.append(alert)
        
        elif summary.margin_level_status == MarginLevel.CRITICAL:
            alert = {
                'type': 'MARGIN_CRITICAL',
                'message': f'WARNING: Margin level at {summary.margin_level:.1f}%. Consider reducing positions.',
                'severity': 'high'
            }
            self.add_alert(alert['type'], alert['message'], alert['severity'])
            new_alerts.append(alert)
        
        elif summary.margin_level_status == MarginLevel.WARNING:
            alert = {
                'type': 'MARGIN_WARNING',
                'message': f'NOTICE: Margin level at {summary.margin_level:.1f}%. Monitor closely.',
                'severity': 'medium'
            }
            self.add_alert(alert['type'], alert['message'], alert['severity'])
            new_alerts.append(alert)
        
        # Check positions at risk
        if summary.positions_at_risk:
            alert = {
                'type': 'POSITION_LIQUIDATION_RISK',
                'message': f'Positions at liquidation risk: {", ".join(summary.positions_at_risk)}',
                'severity': 'high'
            }
            self.add_alert(alert['type'], alert['message'], alert['severity'])
            new_alerts.append(alert)
        
        # Check auto-deleveraging
        deleveraging = self.check_auto_deleveraging()
        if deleveraging:
            alert = {
                'type': 'AUTO_DELEVERAGING_TRIGGERED',
                'message': f'Auto-deleveraging recommended for {deleveraging["symbol"]}',
                'severity': 'high'
            }
            self.add_alert(alert['type'], alert['message'], alert['severity'])
            new_alerts.append(alert)
        
        return new_alerts
    
    def get_recent_alerts(self, limit: int = 10) -> List[Dict]:
        """Get recent alerts."""
        return self._alerts[-limit:]


# Global instance
_margin_monitor: Optional[MarginMonitor] = None


def get_margin_monitor(initial_equity: float = 100000.0) -> MarginMonitor:
    """Get global margin monitor instance."""
    global _margin_monitor
    if _margin_monitor is None:
        _margin_monitor = MarginMonitor(initial_equity=initial_equity)
    return _margin_monitor

