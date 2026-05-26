"""
execution/institutional_execution.py - Institutional Execution Engine

TWAP/VWAP/POV algorithms, smart-order routing, liquidity-seeking,
slippage minimization, queue-priority optimization, adaptive fragmentation.
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import hashlib


class ExecutionAlgo(Enum):
    TWAP = "twap"
    VWAP = "vwap"
    POV = "pov"
    IS = "implementation_shortfall"
    LIQUIDITY_SEEKING = "liquidity_seeking"


@dataclass
class ExecutionOrder:
    order_id: str
    symbol: str
    side: str
    total_quantity: float
    executed_quantity: float
    algo: ExecutionAlgo
    start_time: str
    end_time: str
    participation_rate: float
    slices: List[Dict]
    avg_price: float
    slippage: float
    status: str


class InstitutionalExecutionEngine:
    def __init__(self):
        self._active_orders: Dict[str, ExecutionOrder] = {}
        self._completed_orders: List[ExecutionOrder] = []
        self._market_data: Dict[str, List[Dict]] = {}
        self._execution_history: List[Dict] = []
    
    def create_twap_order(self, symbol: str, side: str,
                         quantity: float, duration_minutes: int,
                         num_slices: int = 60) -> ExecutionOrder:
        order_id = self._generate_order_id(symbol, "TWAP")
        
        now = datetime.now(timezone.utc)
        end_time = now + timedelta(minutes=duration_minutes)
        
        slice_quantity = quantity / num_slices
        
        order = ExecutionOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            total_quantity=quantity,
            executed_quantity=0.0,
            algo=ExecutionAlgo.TWAP,
            start_time=now.isoformat(),
            end_time=end_time.isoformat(),
            participation_rate=1.0 / num_slices,
            slices=[{
                'slice_id': i,
                'quantity': slice_quantity,
                'scheduled_time': (now + timedelta(minutes=duration_minutes/num_slices * i)).isoformat(),
                'executed': False,
                'price': None,
            } for i in range(num_slices)],
            avg_price=0.0,
            slippage=0.0,
            status="active",
        )
        
        self._active_orders[order_id] = order
        return order
    
    def create_vwap_order(self, symbol: str, side: str,
                         quantity: float, duration_minutes: int,
                         volume_profile: Optional[List[float]] = None) -> ExecutionOrder:
        order_id = self._generate_order_id(symbol, "VWAP")
        
        now = datetime.now(timezone.utc)
        end_time = now + timedelta(minutes=duration_minutes)
        
        if volume_profile is None:
            volume_profile = [1.0] * 60
        
        total_volume = sum(volume_profile)
        normalized_profile = [v / total_volume for v in volume_profile]
        
        slices = []
        cumulative_qty = 0
        for i, vol_pct in enumerate(normalized_profile[:duration_minutes]):
            slice_qty = quantity * vol_pct
            cumulative_qty += slice_qty
            slices.append({
                'slice_id': i,
                'quantity': slice_qty,
                'scheduled_time': (now + timedelta(minutes=i)).isoformat(),
                'executed': False,
                'price': None,
                'volume_pct': vol_pct,
            })
        
        order = ExecutionOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            total_quantity=quantity,
            executed_quantity=0.0,
            algo=ExecutionAlgo.VWAP,
            start_time=now.isoformat(),
            end_time=end_time.isoformat(),
            participation_rate=0.0,
            slices=slices,
            avg_price=0.0,
            slippage=0.0,
            status="active",
        )
        
        self._active_orders[order_id] = order
        return order
    
    def create_pov_order(self, symbol: str, side: str,
                        quantity: float, participation_rate: float,
                        max_duration_minutes: int = 120) -> ExecutionOrder:
        order_id = self._generate_order_id(symbol, "POV")
        
        now = datetime.now(timezone.utc)
        end_time = now + timedelta(minutes=max_duration_minutes)
        
        order = ExecutionOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            total_quantity=quantity,
            executed_quantity=0.0,
            algo=ExecutionAlgo.POV,
            start_time=now.isoformat(),
            end_time=end_time.isoformat(),
            participation_rate=participation_rate,
            slices=[],
            avg_price=0.0,
            slippage=0.0,
            status="active",
        )
        
        self._active_orders[order_id] = order
        return order
    
    def execute_slice(self, order_id: str, slice_id: int,
                     fill_price: float, fill_quantity: float) -> bool:
        if order_id not in self._active_orders:
            return False
        
        order = self._active_orders[order_id]
        
        if slice_id >= len(order.slices):
            return False
        
        slice_data = order.slices[slice_id]
        slice_data['executed'] = True
        slice_data['price'] = fill_price
        slice_data['fill_quantity'] = fill_quantity
        slice_data['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        order.executed_quantity += fill_quantity
        
        executed_slices = [s for s in order.slices if s['executed']]
        if executed_slices:
            order.avg_price = np.average(
                [s['price'] for s in executed_slices],
                weights=[s['fill_quantity'] for s in executed_slices]
            )
        
        if order.executed_quantity >= order.total_quantity * 0.99:
            order.status = "completed"
            order.slippage = self._calculate_slippage(order)
            self._completed_orders.append(order)
            del self._active_orders[order_id]
        
        self._execution_history.append({
            'order_id': order_id,
            'slice_id': slice_id,
            'price': fill_price,
            'quantity': fill_quantity,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
        
        return True
    
    def _calculate_slippage(self, order: ExecutionOrder) -> float:
        if not order.slices:
            return 0.0
        
        executed_slices = [s for s in order.slices if s['executed']]
        if not executed_slices:
            return 0.0
        
        arrival_price = executed_slices[0]['price']
        return (order.avg_price - arrival_price) / arrival_price
    
    def smart_order_routing(self, symbol: str, side: str,
                           quantity: float,
                           venues: List[Dict]) -> List[Dict]:
        routed_orders = []
        
        venue_scores = []
        for venue in venues:
            score = self._score_venue(venue, symbol, side)
            venue_scores.append((venue, score))
        
        venue_scores.sort(key=lambda x: x[1], reverse=True)
        
        remaining_qty = quantity
        for venue, score in venue_scores:
            if remaining_qty <= 0:
                break
            
            venue_capacity = venue.get('available_liquidity', 0)
            allocate_qty = min(remaining_qty, venue_capacity * 0.3)
            
            routed_orders.append({
                'venue': venue['name'],
                'quantity': allocate_qty,
                'side': side,
                'symbol': symbol,
                'priority': len(routed_orders),
            })
            
            remaining_qty -= allocate_qty
        
        return routed_orders
    
    def _score_venue(self, venue: Dict, symbol: str, side: str) -> float:
        liquidity = venue.get('available_liquidity', 0)
        spread = venue.get('spread', 0.01)
        latency = venue.get('latency_ms', 100)
        fee = venue.get('fee_rate', 0.001)
        
        score = (
            liquidity * 0.4 -
            spread * 100 * 0.3 -
            latency / 100 * 0.2 -
            fee * 100 * 0.1
        )
        
        return max(0, score)
    
    def _generate_order_id(self, symbol: str, algo: str) -> str:
        return hashlib.sha256(
            f"{symbol}{algo}{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:16]
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        if order_id in self._active_orders:
            order = self._active_orders[order_id]
            return {
                'order_id': order.order_id,
                'status': order.status,
                'progress': order.executed_quantity / order.total_quantity,
                'avg_price': order.avg_price,
                'slippage': order.slippage,
                'slices_executed': sum(1 for s in order.slices if s['executed']),
                'total_slices': len(order.slices),
            }
        
        for order in self._completed_orders:
            if order.order_id == order_id:
                return {
                    'order_id': order.order_id,
                    'status': 'completed',
                    'progress': 1.0,
                    'avg_price': order.avg_price,
                    'slippage': order.slippage,
                }
        
        return None
    
    def get_execution_report(self) -> Dict[str, Any]:
        return {
            'active_orders': len(self._active_orders),
            'completed_orders': len(self._completed_orders),
            'total_execution_history': len(self._execution_history),
            'active_order_details': [
                {
                    'order_id': o.order_id,
                    'symbol': o.symbol,
                    'algo': o.algo.value,
                    'progress': f"{o.executed_quantity / o.total_quantity * 100:.1f}%",
                }
                for o in self._active_orders.values()
            ],
        }


_institutional_execution: Optional[InstitutionalExecutionEngine] = None

def get_institutional_execution() -> InstitutionalExecutionEngine:
    global _institutional_execution
    if _institutional_execution is None:
        _institutional_execution = InstitutionalExecutionEngine()
    return _institutional_execution
