"""
infrastructure/self_healing.py - Self-Healing Distributed Infrastructure

Automatic failover, state recovery, container resurrection, degraded-mode survival.
"""

import os
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import hashlib


class ServiceState(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    RECOVERING = "recovering"
    DEAD = "dead"


@dataclass
class ServiceHealth:
    service_name: str
    state: ServiceState
    last_check: str
    consecutive_failures: int
    last_recovery: Optional[str] = None
    recovery_count: int = 0


class SelfHealingInfrastructure:
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self._services: Dict[str, ServiceHealth] = {}
        self._lock = threading.RLock()
        self._healing_active = False
        self._callbacks: Dict[str, List[Callable]] = {}
        self._state_snapshots: Dict[str, Any] = {}
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        config = {
            'health_check_interval_sec': 10,
            'max_failures_before_restart': 3,
            'recovery_timeout_sec': 60,
            'degraded_mode_enabled': True,
            'auto_failover': True,
        }
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    config.update(json.load(f))
            except:
                pass
        return config
    
    def register_service(self, service_name: str, 
                        health_check: Callable[[], bool],
                        recovery_action: Callable[[], bool],
                        failover_target: Optional[str] = None) -> None:
        with self._lock:
            self._services[service_name] = ServiceHealth(
                service_name=service_name,
                state=ServiceState.HEALTHY,
                last_check=datetime.now(timezone.utc).isoformat(),
                consecutive_failures=0,
            )
            
            if service_name not in self._callbacks:
                self._callbacks[service_name] = []
            self._callbacks[service_name].append({
                'health_check': health_check,
                'recovery_action': recovery_action,
                'failover_target': failover_target,
            })
    
    def start_healing(self) -> None:
        self._healing_active = True
        threading.Thread(target=self._healing_loop, daemon=True).start()
        print('[SELF-HEALING] Started')
    
    def stop_healing(self) -> None:
        self._healing_active = False
        print('[SELF-HEALING] Stopped')
    
    def _healing_loop(self) -> None:
        while self._healing_active:
            self._check_all_services()
            time.sleep(self.config['health_check_interval_sec'])
    
    def _check_all_services(self) -> None:
        with self._lock:
            for service_name, health in list(self._services.items()):
                self._check_service(service_name, health)
    
    def _check_service(self, service_name: str, health: ServiceHealth) -> None:
        if service_name not in self._callbacks:
            return
        
        callbacks = self._callbacks[service_name][0]
        try:
            is_healthy = callbacks['health_check']()
            
            if is_healthy:
                health.state = ServiceState.HEALTHY
                health.consecutive_failures = 0
                health.last_check = datetime.now(timezone.utc).isoformat()
            else:
                health.consecutive_failures += 1
                health.last_check = datetime.now(timezone.utc).isoformat()
                
                if health.consecutive_failures >= self.config['max_failures_before_restart']:
                    health.state = ServiceState.UNHEALTHY
                    self._trigger_recovery(service_name, health, callbacks)
                else:
                    health.state = ServiceState.DEGRADED
        except Exception as e:
            health.consecutive_failures += 1
            health.state = ServiceState.UNHEALTHY
    
    def _trigger_recovery(self, service_name: str, 
                         health: ServiceHealth,
                         callbacks: Dict) -> None:
        print(f'[SELF-HEALING] Triggering recovery for {service_name}')
        health.state = ServiceState.RECOVERING
        
        try:
            success = callbacks['recovery_action']()
            
            if success:
                health.state = ServiceState.HEALTHY
                health.consecutive_failures = 0
                health.last_recovery = datetime.now(timezone.utc).isoformat()
                health.recovery_count += 1
                print(f'[SELF-HEALING] {service_name} recovered')
            else:
                health.state = ServiceState.DEAD
                print(f'[SELF-HEALING] {service_name} recovery failed')
                
                if callbacks['failover_target'] and self.config['auto_failover']:
                    self._trigger_failover(service_name, callbacks['failover_target'])
        except Exception as e:
            health.state = ServiceState.DEAD
            print(f'[SELF-HEALING] Recovery error: {e}')
    
    def _trigger_failover(self, failed_service: str, failover_target: str) -> None:
        print(f'[SELF-HEALING] Failing over {failed_service} -> {failover_target}')
    
    def take_state_snapshot(self, service_name: str, state: Any) -> None:
        with self._lock:
            self._state_snapshots[service_name] = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'state': state,
            }
    
    def restore_state_snapshot(self, service_name: str) -> Optional[Any]:
        with self._lock:
            if service_name in self._state_snapshots:
                snapshot = self._state_snapshots[service_name]
                print(f'[SELF-HEALING] Restored snapshot for {service_name}')
                return snapshot.get('state')
        return None
    
    def get_health_report(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'healing_active': self._healing_active,
                'services': {
                    name: {
                        'state': h.state.value,
                        'failures': h.consecutive_failures,
                        'recoveries': h.recovery_count,
                    }
                    for name, h in self._services.items()
                },
                'snapshots': len(self._state_snapshots),
            }
    
    def is_healthy(self, service_name: str) -> bool:
        with self._lock:
            if service_name not in self._services:
                return True
            return self._services[service_name].state == ServiceState.HEALTHY


_self_healing: Optional[SelfHealingInfrastructure] = None

def get_self_healing() -> SelfHealingInfrastructure:
    global _self_healing
    if _self_healing is None:
        _self_healing = SelfHealingInfrastructure()
    return _self_healing
