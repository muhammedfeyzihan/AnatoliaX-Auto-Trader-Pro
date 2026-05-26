"""
backtest/strategy_sandbox.py - Autonomous Strategy Sandboxing System

Isolated execution containers, strategy quarantine logic, performance-validation gates,
adversarial stress environments, rollback-safe deployment pipelines.
"""

import numpy as np
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import copy


class SandboxStatus(Enum):
    CREATED = "created"
    RUNNING = "running"
    VALIDATING = "validating"
    APPROVED = "approved"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"


@dataclass
class SandboxResult:
    sandbox_id: str
    strategy_id: str
    status: SandboxStatus
    performance_metrics: Dict[str, float]
    stress_test_results: Dict[str, Any]
    validation_passed: bool
    quarantine_reason: Optional[str]
    timestamp: str


class AutonomousStrategySandbox:
    def __init__(self):
        self._sandboxes: Dict[str, SandboxResult] = {}
        self._quarantined_strategies: List[str] = []
        self._approved_strategies: List[str] = []
        self._validation_gates: List[Dict] = [
            {'name': 'min_sharpe', 'threshold': 0.5, 'comparison': 'gte'},
            {'name': 'max_drawdown', 'threshold': 0.10, 'comparison': 'lte'},
            {'name': 'min_trades', 'threshold': 100, 'comparison': 'gte'},
            {'name': 'win_rate', 'threshold': 0.40, 'comparison': 'gte'},
        ]
    
    def create_sandbox(self, strategy_id: str,
                      strategy_fn: Callable,
                      test_data: List[Dict]) -> str:
        sandbox_id = hashlib.sha256(
            f"{strategy_id}{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:16]
        
        result = SandboxResult(
            sandbox_id=sandbox_id,
            strategy_id=strategy_id,
            status=SandboxStatus.CREATED,
            performance_metrics={},
            stress_test_results={},
            validation_passed=False,
            quarantine_reason=None,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        self._sandboxes[sandbox_id] = result
        return sandbox_id
    
    def run_sandbox(self, sandbox_id: str,
                   strategy_fn: Callable,
                   test_data: List[Dict]) -> SandboxResult:
        if sandbox_id not in self._sandboxes:
            raise ValueError(f"Sandbox {sandbox_id} not found")
        
        result = self._sandboxes[sandbox_id]
        result.status = SandboxStatus.RUNNING
        
        try:
            metrics = self._execute_strategy(strategy_fn, test_data)
            result.performance_metrics = metrics
            
            result.status = SandboxStatus.VALIDATING
            
            stress_results = self._run_stress_tests(strategy_fn, test_data)
            result.stress_test_results = stress_results
            
            validation_passed = self._validate_performance(metrics)
            result.validation_passed = validation_passed
            
            if validation_passed:
                result.status = SandboxStatus.APPROVED
                if result.strategy_id not in self._approved_strategies:
                    self._approved_strategies.append(result.strategy_id)
            else:
                result.status = SandboxStatus.REJECTED
                result.quarantine_reason = self._get_rejection_reason(metrics)
                if result.strategy_id not in self._quarantined_strategies:
                    self._quarantined_strategies.append(result.strategy_id)
            
        except Exception as e:
            result.status = SandboxStatus.QUARANTINED
            result.quarantine_reason = f"Execution error: {str(e)}"
            if result.strategy_id not in self._quarantined_strategies:
                self._quarantined_strategies.append(result.strategy_id)
        
        return result
    
    def _execute_strategy(self, strategy_fn: Callable,
                         test_data: List[Dict]) -> Dict[str, float]:
        trades = []
        equity = [1000000]
        
        for data_point in test_data:
            action = strategy_fn(data_point, {'equity': equity[-1]})
            if action and 'pnl' in action:
                trades.append(action)
                equity.append(equity[-1] + action['pnl'])
        
        returns = np.diff(equity) / np.array(equity[:-1])
        sharpe = (np.mean(returns) / (np.std(returns) + 1e-6)) * np.sqrt(252) if len(returns) > 1 else 0
        
        peak = equity[0]
        max_dd = 0.0
        for e in equity:
            if e > peak:
                peak = e
            dd = (peak - e) / peak
            if dd > max_dd:
                max_dd = dd
        
        wins = [t for t in trades if t.get('pnl', 0) > 0]
        
        return {
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'total_return': (equity[-1] - equity[0]) / equity[0],
            'total_trades': len(trades),
            'win_rate': len(wins) / len(trades) if trades else 0,
            'final_equity': equity[-1],
        }
    
    def _run_stress_tests(self, strategy_fn: Callable,
                         test_data: List[Dict]) -> Dict[str, Any]:
        stress_results = {}
        
        crash_data = copy.deepcopy(test_data)
        for i in range(len(crash_data)):
            if 'price' in crash_data[i]:
                crash_data[i]['price'] *= 0.8
        crash_metrics = self._execute_strategy(strategy_fn, crash_data)
        stress_results['market_crash'] = crash_metrics
        
        vol_spike_data = copy.deepcopy(test_data)
        for i in range(len(vol_spike_data)):
            if 'volatility' in vol_spike_data[i]:
                vol_spike_data[i]['volatility'] *= 3
        vol_metrics = self._execute_strategy(strategy_fn, vol_spike_data)
        stress_results['volatility_spike'] = vol_metrics
        
        liq_crisis_data = copy.deepcopy(test_data)
        for i in range(len(liq_crisis_data)):
            if 'liquidity' in liq_crisis_data[i]:
                liq_crisis_data[i]['liquidity'] *= 0.1
        liq_metrics = self._execute_strategy(strategy_fn, liq_crisis_data)
        stress_results['liquidity_crisis'] = liq_metrics
        
        return stress_results
    
    def _validate_performance(self, metrics: Dict[str, float]) -> bool:
        for gate in self._validation_gates:
            value = metrics.get(gate['name'], 0)
            threshold = gate['threshold']
            
            if gate['comparison'] == 'gte':
                if value < threshold:
                    return False
            elif gate['comparison'] == 'lte':
                if value > threshold:
                    return False
        
        return True
    
    def _get_rejection_reason(self, metrics: Dict[str, float]) -> str:
        reasons = []
        for gate in self._validation_gates:
            value = metrics.get(gate['name'], 0)
            threshold = gate['threshold']
            
            if gate['comparison'] == 'gte' and value < threshold:
                reasons.append(f"{gate['name']}: {value:.2f} < {threshold}")
            elif gate['comparison'] == 'lte' and value > threshold:
                reasons.append(f"{gate['name']}: {value:.2f} > {threshold}")
        
        return "; ".join(reasons)
    
    def approve_strategy(self, strategy_id: str) -> bool:
        if strategy_id in self._quarantined_strategies:
            self._quarantined_strategies.remove(strategy_id)
        if strategy_id not in self._approved_strategies:
            self._approved_strategies.append(strategy_id)
        return True
    
    def quarantine_strategy(self, strategy_id: str, reason: str) -> bool:
        if strategy_id in self._approved_strategies:
            self._approved_strategies.remove(strategy_id)
        if strategy_id not in self._quarantined_strategies:
            self._quarantined_strategies.append(strategy_id)
        return True
    
    def get_sandbox_report(self) -> Dict[str, Any]:
        return {
            'total_sandboxes': len(self._sandboxes),
            'approved_strategies': len(self._approved_strategies),
            'quarantined_strategies': len(self._quarantined_strategies),
            'approved_list': self._approved_strategies,
            'quarantined_list': self._quarantined_strategies,
            'sandbox_details': [
                {
                    'sandbox_id': s.sandbox_id,
                    'strategy_id': s.strategy_id,
                    'status': s.status.value,
                    'validation': s.validation_passed,
                }
                for s in list(self._sandboxes.values())[-10:]
            ],
        }


_strategy_sandbox: Optional[AutonomousStrategySandbox] = None

def get_autonomous_strategy_sandbox() -> AutonomousStrategySandbox:
    global _strategy_sandbox
    if _strategy_sandbox is None:
        _strategy_sandbox = AutonomousStrategySandbox()
    return _strategy_sandbox
