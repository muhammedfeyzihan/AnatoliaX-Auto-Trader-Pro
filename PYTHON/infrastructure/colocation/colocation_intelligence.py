"""
infrastructure/colocation/colocation_intelligence.py — RTT measurement and routing intelligence
"""
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class RTTAlert:
    alert: bool
    message: str
    current_rtt: float
    baseline_rtt: float
    degradation_pct: float


class ColocationIntelligence:
    """
    Colocation intelligence for optimal routing decisions.
    
    Tracks RTT (Round-Trip Time) between exchanges and data centers,
    maintains baselines, and triggers alerts when latency degrades.
    """
    
    def __init__(self):
        self._rtt_matrix: Dict[str, Dict[str, float]] = {}  # market -> region -> rtt
        self._baselines: Dict[str, float] = {}  # market -> baseline_rtt
        self._alert_threshold_pct: float = 50.0  # Alert if RTT degrades > 50%
    
    def measure_rtt(self, market: str, region: str, rtt_us: float) -> None:
        """Record RTT measurement for a market-region pair."""
        if market not in self._rtt_matrix:
            self._rtt_matrix[market] = {}
        
        self._rtt_matrix[market][region] = rtt_us
        
        # Update baseline if this is the first measurement or better than current
        if market not in self._baselines or rtt_us < self._baselines[market]:
            self._baselines[market] = rtt_us
    
    def best_region(self, market: str) -> str:
        """Get the region with lowest RTT for a given market."""
        if market not in self._rtt_matrix or not self._rtt_matrix[market]:
            return "unknown"
        
        return min(self._rtt_matrix[market], key=self._rtt_matrix[market].get)
    
    def route_investigation(self, market: str, current_rtt: float) -> Optional[Dict[str, Any]]:
        """
        Check if current RTT triggers a routing investigation alert.
        
        Returns alert dict if RTT degradation exceeds threshold, None otherwise.
        """
        if market not in self._baselines:
            return None
        
        baseline = self._baselines[market]
        if baseline == 0:
            return None
        
        degradation_pct = ((current_rtt - baseline) / baseline) * 100
        
        if degradation_pct > self._alert_threshold_pct:
            return {
                "alert": True,
                "message": f"RTT degradation detected for {market}",
                "current_rtt": current_rtt,
                "baseline_rtt": baseline,
                "degradation_pct": degradation_pct,
            }
        
        # Return None when no alert (as tests expect)
        return None
    
    def get_heatmap(self) -> Dict[str, Dict[str, float]]:
        """Return the RTT heatmap (alias for rtt_matrix)."""
        return self._rtt_matrix.copy()
    
    def get_rtt_matrix(self) -> Dict[str, Dict[str, float]]:
        """Return the full RTT matrix."""
        return self._rtt_matrix.copy()
    
    def get_baselines(self) -> Dict[str, float]:
        """Return baseline RTTs."""
        return self._baselines.copy()
    
    def set_alert_threshold(self, threshold_pct: float) -> None:
        """Set the alert threshold percentage."""
        self._alert_threshold_pct = threshold_pct
