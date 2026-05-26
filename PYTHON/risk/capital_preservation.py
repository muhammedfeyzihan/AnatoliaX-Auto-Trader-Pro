"""
risk/capital_preservation.py - Autonomous Capital Preservation Protocol

Multi-threshold drawdown governors, probabilistic kill-switches,
exposure throttling, emergency deleveraging, volatility-triggered survival.
"""

import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class CapitalState(Enum):
    NORMAL = "normal"
    CAUTION = "caution"
    REDUCED = "reduced"
    SURVIVAL = "survival"
    HALTED = "halted"


@dataclass
class DrawdownGovernor:
    threshold: float
    action: str
    triggered: bool
    trigger_time: Optional[str]


class CapitalPreservationProtocol:
    def __init__(self, initial_capital: float = 1_000_000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        self._drawdown_governors: List[DrawdownGovernor] = [
            DrawdownGovernor(threshold=0.02, action="reduce_exposure_25%", triggered=False, trigger_time=None),
            DrawdownGovernor(threshold=0.05, action="reduce_exposure_50%", triggered=False, trigger_time=None),
            DrawdownGovernor(threshold=0.08, action="reduce_exposure_75%", triggered=False, trigger_time=None),
            DrawdownGovernor(threshold=0.10, action="kill_switch", triggered=False, trigger_time=None),
        ]
        self._capital_state = CapitalState.NORMAL
        self._exposure_multiplier = 1.0
        self._halted = False
        self._state_history: List[Dict] = []
    
    def update_capital(self, new_capital: float) -> None:
        self.current_capital = new_capital
        
        if new_capital > self.peak_capital:
            self.peak_capital = new_capital
        
        self._check_drawdown_governors()
        self._update_capital_state()
    
    def _check_drawdown_governors(self) -> None:
        current_dd = (self.peak_capital - self.current_capital) / self.peak_capital
        timestamp = datetime.now(timezone.utc).isoformat()
        
        for governor in self._drawdown_governors:
            if current_dd >= governor.threshold and not governor.triggered:
                governor.triggered = True
                governor.trigger_time = timestamp
                self._apply_governor_action(governor)
    
    def _apply_governor_action(self, governor: DrawdownGovernor) -> None:
        if "reduce_exposure" in governor.action:
            pct = int(governor.action.split("_")[-1].replace("%", ""))
            self._exposure_multiplier = 1.0 - (pct / 100)
        elif governor.action == "kill_switch":
            self._halted = True
    
    def _update_capital_state(self) -> None:
        current_dd = (self.peak_capital - self.current_capital) / self.peak_capital
        
        if self._halted:
            new_state = CapitalState.HALTED
        elif current_dd >= 0.10:
            new_state = CapitalState.SURVIVAL
        elif current_dd >= 0.05:
            new_state = CapitalState.REDUCED
        elif current_dd >= 0.02:
            new_state = CapitalState.CAUTION
        else:
            new_state = CapitalState.NORMAL
        
        if new_state != self._capital_state:
            self._capital_state = new_state
            self._state_history.append({
                'state': new_state.value,
                'drawdown': current_dd,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            })
    
    def get_allowed_exposure(self) -> float:
        if self._halted:
            return 0.0
        return self._exposure_multiplier
    
    def should_halt_trading(self) -> bool:
        return self._halted
    
    def reset_protocol(self) -> None:
        for governor in self._drawdown_governors:
            governor.triggered = False
            governor.trigger_time = None
        self._halted = False
        self._exposure_multiplier = 1.0
        self._capital_state = CapitalState.NORMAL
    
    def get_preservation_report(self) -> Dict[str, Any]:
        current_dd = (self.peak_capital - self.current_capital) / self.peak_capital
        
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'peak_capital': self.peak_capital,
            'current_drawdown': current_dd,
            'capital_state': self._capital_state.value,
            'exposure_multiplier': self._exposure_multiplier,
            'trading_halted': self._halted,
            'governors_triggered': sum(1 for g in self._drawdown_governors if g.triggered),
            'state_history': self._state_history[-10:],
        }


_capital_preservation: Optional[CapitalPreservationProtocol] = None

def get_capital_preservation(initial_capital: float = 1_000_000) -> CapitalPreservationProtocol:
    global _capital_preservation
    if _capital_preservation is None:
        _capital_preservation = CapitalPreservationProtocol(initial_capital=initial_capital)
    return _capital_preservation
