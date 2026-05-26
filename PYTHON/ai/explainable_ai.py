"""
ai/explainable_ai.py - Explainable AI Framework

Generates causal trade reasoning, confidence scoring, feature attribution.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import hashlib


@dataclass
class TradeExplanation:
    trade_id: str
    decision: str
    confidence: float
    reasoning: str
    feature_attribution: Dict[str, float]
    risk_factors: List[str]
    timestamp: str


@dataclass
class FeatureImportance:
    feature_name: str
    importance_score: float
    direction: str
    stability: float


class ExplainableAI:
    def __init__(self):
        self._explanations: List[TradeExplanation] = []
        self._feature_importance: Dict[str, FeatureImportance] = {}
        self._decision_history: List[Dict] = []
    
    def explain_trade(self, signal: Dict[str, Any], 
                     features: Dict[str, float],
                     decision: str,
                     confidence: float) -> TradeExplanation:
        trade_id = hashlib.sha256(
            f"{decision}{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:16]
        
        reasoning = self._generate_reasoning(signal, features, decision)
        feature_attr = self._calculate_feature_attribution(features, decision)
        risk_factors = self._identify_risk_factors(signal, features)
        
        explanation = TradeExplanation(
            trade_id=trade_id,
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
            feature_attribution=feature_attr,
            risk_factors=risk_factors,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        self._explanations.append(explanation)
        self._update_feature_importance(features, decision)
        
        return explanation
    
    def _generate_reasoning(self, signal: Dict, 
                           features: Dict[str, float],
                           decision: str) -> str:
        reasons = []
        
        if 'rsi' in features:
            rsi = features['rsi']
            if rsi < 30:
                reasons.append("RSI indicates oversold condition")
            elif rsi > 70:
                reasons.append("RSI indicates overbought condition")
        
        if 'macd_signal' in features:
            if features['macd_signal'] > 0:
                reasons.append("MACD shows bullish momentum")
            else:
                reasons.append("MACD shows bearish momentum")
        
        if 'volume_ratio' in features and features['volume_ratio'] > 2.0:
            reasons.append("Unusual volume detected")
        
        if 'regime' in signal:
            reasons.append(f"Market regime: {signal['regime']}")
        
        return f"Decision: {decision}. " + "; ".join(reasons) + "."
    
    def _calculate_feature_attribution(self, features: Dict[str, float],
                                       decision: str) -> Dict[str, float]:
        attribution = {}
        total = sum(abs(v) for v in features.values()) + 1e-6
        
        for feature, value in features.items():
            attribution[feature] = abs(value) / total
        
        return attribution
    
    def _identify_risk_factors(self, signal: Dict,
                              features: Dict[str, float]) -> List[str]:
        risks = []
        
        if 'volatility' in features and features['volatility'] > 0.05:
            risks.append("High volatility")
        
        if 'liquidity' in features and features['liquidity'] < 0.5:
            risks.append("Low liquidity")
        
        if signal.get('regime') == 'crisis':
            risks.append("Crisis regime")
        
        return risks
    
    def _update_feature_importance(self, features: Dict[str, float],
                                   decision: str) -> None:
        for feature, value in features.items():
            if feature not in self._feature_importance:
                self._feature_importance[feature] = FeatureImportance(
                    feature_name=feature,
                    importance_score=0.0,
                    direction="neutral",
                    stability=1.0,
                )
            
            fi = self._feature_importance[feature]
            fi.importance_score = (fi.importance_score * 0.9 + abs(value) * 0.1)
            fi.direction = "positive" if value > 0 else "negative"
    
    def get_explanation(self, trade_id: str) -> Optional[TradeExplanation]:
        for exp in self._explanations:
            if exp.trade_id == trade_id:
                return exp
        return None
    
    def get_feature_importance_ranking(self) -> List[FeatureImportance]:
        return sorted(
            self._feature_importance.values(),
            key=lambda x: x.importance_score,
            reverse=True,
        )
    
    def get_explainability_report(self) -> Dict[str, Any]:
        return {
            'total_explanations': len(self._explanations),
            'features_tracked': len(self._feature_importance),
            'top_features': [
                {'name': f.feature_name, 'importance': f.importance_score}
                for f in self.get_feature_importance_ranking()[:10]
            ],
        }


_xai: Optional[ExplainableAI] = None

def get_explainable_ai() -> ExplainableAI:
    global _xai
    if _xai is None:
        _xai = ExplainableAI()
    return _xai
