"""
explainable_ai.py — SHAP-like trade explanations.
K236: ExplainableAI.
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import json


@dataclass
class Explanation:
    decision: str = ""
    confidence: float = 0.0
    top_features: List[Dict] = field(default_factory=list)
    direction: str = ""
    summary: str = ""


class ExplainableAI:
    """
    Trade kararlarini aciklayan basit explainability motoru.
    Feature onem skorlari + dogal dil ozeti.
    """

    def __init__(self, top_n: int = 5):
        self.top_n = top_n

    def explain_trade(
        self,
        decision: str,
        confidence: float,
        features: Dict[str, float],
        weights: Optional[Dict[str, float]] = None,
    ) -> Explanation:
        """
        features: {"rsi": 65, "volume_z": 2.5, ...}
        weights: opsiyonel agirliklar
        """
        if weights is None:
            weights = {k: 1.0 for k in features}

        # Score = feature_value * weight
        scored = []
        for k, v in features.items():
            w = weights.get(k, 1.0)
            impact = abs(v) * w
            scored.append({"feature": k, "value": v, "weight": w, "impact": impact})

        scored.sort(key=lambda x: x["impact"], reverse=True)
        top = scored[:self.top_n]

        direction = "BUY" if confidence > 0.5 else "SELL" if confidence < -0.5 else "HOLD"
        summary = self._generate_summary(decision, top, direction)

        return Explanation(
            decision=decision,
            confidence=confidence,
            top_features=top,
            direction=direction,
            summary=summary,
        )

    def explain_rejection(self, reason: str, checks: Dict[str, bool]) -> Explanation:
        failed = [k for k, v in checks.items() if not v]
        top = [{"feature": k, "value": 0, "weight": 1.0, "impact": 1.0} for k in failed]
        return Explanation(
            decision="REJECTED",
            confidence=0.0,
            top_features=top,
            direction="NONE",
            summary=f"Islem reddedildi: {reason}. Basarisiz kontroller: {', '.join(failed)}",
        )

    def _generate_summary(self, decision: str, top_features: List[Dict], direction: str) -> str:
        parts = [f"Karar: {decision} ({direction})"]
        for feat in top_features[:3]:
            parts.append(f"{feat['feature']}={feat['value']:.2f} (etki: {feat['impact']:.2f})")
        return "; ".join(parts)
