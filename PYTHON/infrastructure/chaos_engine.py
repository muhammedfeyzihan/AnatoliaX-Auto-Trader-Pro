"""
infrastructure/chaos_engine.py - Chaos Engineering Infrastructure

Intentionally triggers failures to validate autonomous resilience.
"""

import os
import time
import random
import threading
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import hashlib


class FailureType(Enum):
    DATABASE_CRASH = "database_crash"
    WEBSOCKET_DISCONNECT = "websocket_disconnect"
    API_TIMEOUT = "api_timeout"
    API_RATE_LIMIT = "api_rate_limit"
    MEMORY_LEAK = "memory_leak"
    CPU_SPIKE = "cpu_spike"
    NETWORK_PARTITION = "network_partition"
    NETWORK_LATENCY = "network_latency"
    EXCHANGE_HALT = "exchange_halt"
    DATA_CORRUPTION = "data_corruption"
    ORDER_REJECT = "order_reject"
    PARTIAL_FILL = "partial_fill"
    STALE_ORDER = "stale_order"
    LATENCY_SPIKE = "latency_spike"
    RECONNECT_STORM = "reconnect_storm"


@dataclass
class ChaosEvent:
    event_id: str
    failure_type: FailureType
    start_time: str
    duration_sec: float
    severity: str
    target_service: str
    success: bool
    recovery_time_sec: Optional[float] = None
    notes: str = ""


class ChaosEngine:
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self._active_failures: Dict[str, ChaosEvent] = {}
        self._failure_history: List[ChaosEvent] = []
        self._service_health: Dict[str, bool] = {}
        self._lock = threading.RLock()
        self._chaos_mode = False
        self._callbacks: Dict[FailureType, List[Callable]] = {}
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        config = {
            'chaos_probability': 0.1,
            'max_concurrent_failures': 3,
            'excluded_services': [],
        }
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    loaded = json.load(f)
                    config.update(loaded)
            except:
                pass
        return config
    
    def enable_chaos_mode(self) -> None:
        self._chaos_mode = True
        print('[CHAOS] Chaos mode ENABLED')
    
    def disable_chaos_mode(self) -> None:
        self._chaos_mode = False
        self.recover_all()
        print('[CHAOS] Chaos mode DISABLED')
    
    def inject_failure(self, failure_type: FailureType, 
                      duration_sec: float = 60.0,
                      severity: str = 'medium',
                      target_service: str = 'all',
                      callback: Optional[Callable] = None) -> Optional[ChaosEvent]:
        with self._lock:
            if not self._chaos_mode:
                return None
            
            event_id = hashlib.sha256(
                f"{failure_type.value}{time.time()}".encode()
            ).hexdigest()[:16]
            
            event = ChaosEvent(
                event_id=event_id,
                failure_type=failure_type,
                start_time=datetime.now(timezone.utc).isoformat(),
                duration_sec=duration_sec,
                severity=severity,
                target_service=target_service,
                success=False,
            )
            
            try:
                self._execute_failure(failure_type, target_service)
                event.success = True
                print(f'[CHAOS] Injected {failure_type.value}')
            except Exception as e:
                print(f'[CHAOS] Failed: {e}')
            
            self._active_failures[event_id] = event
            self._failure_history.append(event)
            
            threading.Timer(duration_sec, self._recover_failure, args=[event_id]).start()
            return event
    
    def _execute_failure(self, failure_type: FailureType, target_service: str) -> None:
        if failure_type in self._callbacks:
            for cb in self._callbacks[failure_type]:
                try:
                    cb(failure_type, target_service)
                except:
                    pass
        
        if failure_type == FailureType.WEBSOCKET_DISCONNECT:
            self._service_health[f"{target_service}_ws"] = False
        elif failure_type == FailureType.API_TIMEOUT:
            self._service_health[f"{target_service}_api"] = False
        elif failure_type == FailureType.NETWORK_LATENCY:
            time.sleep(2.0)
        elif failure_type == FailureType.DATA_CORRUPTION:
            self._service_health[f"{target_service}_data"] = False
        elif failure_type == FailureType.PARTIAL_FILL:
            self._service_health[f"{target_service}_partial"] = True
        elif failure_type == FailureType.LATENCY_SPIKE:
            time.sleep(5.0)
    
    def _recover_failure(self, event_id: str) -> None:
        with self._lock:
            if event_id not in self._active_failures:
                return
            
            event = self._active_failures[event_id]
            event.recovery_time_sec = time.time() - datetime.fromisoformat(
                event.start_time.replace('+00:00', '')
            ).timestamp()
            
            self._service_health[f"{event.target_service}_ws"] = True
            self._service_health[f"{event.target_service}_api"] = True
            
            del self._active_failures[event_id]
            print(f'[CHAOS] Recovered {event.failure_type.value}')
    
    def recover_all(self) -> None:
        with self._lock:
            for event_id in list(self._active_failures.keys()):
                self._recover_failure(event_id)
    
    def register_callback(self, failure_type: FailureType, callback: Callable) -> None:
        if failure_type not in self._callbacks:
            self._callbacks[failure_type] = []
        self._callbacks[failure_type].append(callback)
    
    def run_chaos_test(self, duration_sec: float = 300.0, failure_count: int = 5) -> Dict[str, Any]:
        print(f'[CHAOS] Starting test: {duration_sec}s, {failure_count} failures')
        self.enable_chaos_mode()
        
        for i in range(failure_count):
            failure_type = random.choice(list(FailureType))
            duration = random.uniform(10.0, 60.0)
            self.inject_failure(failure_type, duration, 'medium', 'trading_engine')
            time.sleep(duration_sec / failure_count)
        
        time.sleep(duration_sec)
        self.disable_chaos_mode()
        return self.get_chaos_report()
    
    def get_chaos_report(self) -> Dict[str, Any]:
        return {
            'chaos_mode': self._chaos_mode,
            'active_failures': len(self._active_failures),
            'total_failures': len(self._failure_history),
            'service_health': self._service_health.copy(),
        }
    
    def is_service_healthy(self, service: str) -> bool:
        return self._service_health.get(f"{service}_ws", True) and \
               self._service_health.get(f"{service}_api", True)


_chaos_engine: Optional[ChaosEngine] = None

def get_chaos_engine() -> ChaosEngine:
    global _chaos_engine
    if _chaos_engine is None:
        _chaos_engine = ChaosEngine()
    return _chaos_engine
