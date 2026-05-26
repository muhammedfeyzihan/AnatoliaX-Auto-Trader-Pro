"""
security/exchange_defense.py - Exchange Defense Security Layer

Detects API poisoning, fake liquidity, latency manipulation, adversarial attacks.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import time


@dataclass
class SecurityAlert:
    alert_id: str
    alert_type: str
    severity: str
    description: str
    timestamp: str
    affected_service: str
    action_taken: str


@dataclass
class ThreatMetrics:
    service_name: str
    api_poisoning_score: float
    fake_liquidity_score: float
    latency_manipulation_score: float
    abnormal_execution_score: float
    manipulation_attempt_score: float
    overall_threat_level: str


class ExchangeDefenseLayer:
    def __init__(self):
        self._alerts: List[SecurityAlert] = []
        self._threat_metrics: Dict[str, ThreatMetrics] = {}
        self._baseline_metrics: Dict[str, float] = {}
        self._blocked_ips: List[str] = []
        self._suspicious_patterns: List[Dict] = []
    
    def analyze_api_response(self, service: str, response: Dict,
                            response_time_ms: float) -> Optional[SecurityAlert]:
        if service not in self._baseline_metrics:
            self._baseline_metrics[service] = response_time_ms
        
        baseline = self._baseline_metrics[service]
        
        if response_time_ms > baseline * 5:
            alert = self._create_alert(
                alert_type="api_poisoning",
                severity="high",
                description=f"API response time {response_time_ms}ms exceeds baseline {baseline}ms",
                affected_service=service,
                action_taken="flagged_for_review",
            )
            return alert
        
        if 'error' in response and response.get('error') == 'invalid_signature':
            alert = self._create_alert(
                alert_type="api_poisoning",
                severity="critical",
                description="API signature validation failed",
                affected_service=service,
                action_taken="blocked",
            )
            return alert
        
        return None
    
    def analyze_liquidity(self, service: str, bid_size: float, ask_size: float,
                         spread: float) -> Optional[SecurityAlert]:
        if service not in self._threat_metrics:
            self._threat_metrics[service] = ThreatMetrics(
                service_name=service,
                api_poisoning_score=0.0,
                fake_liquidity_score=0.0,
                latency_manipulation_score=0.0,
                abnormal_execution_score=0.0,
                manipulation_attempt_score=0.0,
                overall_threat_level="low",
            )
        
        metrics = self._threat_metrics[service]
        
        if bid_size > 100000 or ask_size > 100000:
            metrics.fake_liquidity_score = min(1.0, metrics.fake_liquidity_score + 0.1)
        
        if spread > 0.01:
            metrics.fake_liquidity_score = min(1.0, metrics.fake_liquidity_score + 0.05)
        
        if metrics.fake_liquidity_score > 0.7:
            alert = self._create_alert(
                alert_type="fake_liquidity",
                severity="high",
                description=f"Fake liquidity detected on {service}",
                affected_service=service,
                action_taken="liquidity_filter_enabled",
            )
            return alert
        
        return None
    
    def analyze_latency(self, service: str, latency_ms: float) -> Optional[SecurityAlert]:
        if latency_ms > 1000:
            alert = self._create_alert(
                alert_type="latency_manipulation",
                severity="medium",
                description=f"Abnormal latency {latency_ms}ms on {service}",
                affected_service=service,
                action_taken="latency_compensation_applied",
            )
            return alert
        
        return None
    
    def analyze_execution(self, service: str, fill_rate: float,
                         slippage: float) -> Optional[SecurityAlert]:
        if fill_rate < 0.5:
            alert = self._create_alert(
                alert_type="abnormal_execution",
                severity="medium",
                description=f"Low fill rate {fill_rate*100:.1f}% on {service}",
                affected_service=service,
                action_taken="execution_review",
            )
            return alert
        
        if slippage > 0.01:
            alert = self._create_alert(
                alert_type="abnormal_execution",
                severity="high",
                description=f"High slippage {slippage*100:.2f}% on {service}",
                affected_service=service,
                action_taken="slippage_limit_applied",
            )
            return alert
        
        return None
    
    def _create_alert(self, alert_type: str, severity: str,
                     description: str, affected_service: str,
                     action_taken: str) -> SecurityAlert:
        alert_id = hashlib.sha256(
            f"{alert_type}{time.time()}{description}".encode()
        ).hexdigest()[:16]
        
        alert = SecurityAlert(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            description=description,
            timestamp=datetime.now(timezone.utc).isoformat(),
            affected_service=affected_service,
            action_taken=action_taken,
        )
        
        self._alerts.append(alert)
        print(f"[SECURITY] Alert: {alert_type} - {severity} - {description}")
        return alert
    
    def get_threat_level(self, service: str) -> str:
        if service in self._threat_metrics:
            return self._threat_metrics[service].overall_threat_level
        return "unknown"
    
    def get_security_report(self) -> Dict[str, Any]:
        return {
            'total_alerts': len(self._alerts),
            'services_monitored': len(self._threat_metrics),
            'blocked_ips': len(self._blocked_ips),
            'alerts_by_type': self._count_alerts_by_type(),
            'recent_alerts': [
                {
                    'id': a.alert_id,
                    'type': a.alert_type,
                    'severity': a.severity,
                    'service': a.affected_service,
                }
                for a in self._alerts[-10:]
            ],
        }
    
    def _count_alerts_by_type(self) -> Dict[str, int]:
        counts = {}
        for alert in self._alerts:
            if alert.alert_type not in counts:
                counts[alert.alert_type] = 0
            counts[alert.alert_type] += 1
        return counts


_defense_layer: Optional[ExchangeDefenseLayer] = None

def get_exchange_defense() -> ExchangeDefenseLayer:
    global _defense_layer
    if _defense_layer is None:
        _defense_layer = ExchangeDefenseLayer()
    return _defense_layer
