"""
ai/ai_governance.py - AI Governance Framework

Policy constraints, autonomous risk ethics enforcement, explainability compliance,
bounded optimization controls, deterministic human-override infrastructure.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib


class GovernancePolicy(Enum):
    MAX_POSITION_SIZE = "max_position_size"
    MAX_DRAWDOWN = "max_drawdown"
    MAX_LEVERAGE = "max_leverage"
    RESTRICTED_ASSETS = "restricted_assets"
    REQUIRED_EXPLAINABILITY = "required_explainability"
    HUMAN_OVERRIDE = "human_override"
    RISK_ETHICS = "risk_ethics"


@dataclass
class PolicyConstraint:
    policy_id: str
    policy_type: GovernancePolicy
    threshold: float
    enabled: bool
    violations: int
    last_violation: Optional[str]


@dataclass
class GovernanceDecision:
    decision_id: str
    ai_decision: Dict[str, Any]
    policy_check_passed: bool
    violated_policies: List[str]
    human_override_available: bool
    explanation_required: bool
    timestamp: str
    approved: bool


class AIGovernanceFramework:
    def __init__(self):
        self._policies: List[PolicyConstraint] = []
        self._decisions: List[GovernanceDecision] = []
        self._human_override_active = False
        self._violation_count = 0
        self._initialize_default_policies()
    
    def _initialize_default_policies(self) -> None:
        self._policies = [
            PolicyConstraint(
                policy_id="pol_001",
                policy_type=GovernancePolicy.MAX_POSITION_SIZE,
                threshold=0.02,
                enabled=True,
                violations=0,
                last_violation=None,
            ),
            PolicyConstraint(
                policy_id="pol_002",
                policy_type=GovernancePolicy.MAX_DRAWDOWN,
                threshold=0.10,
                enabled=True,
                violations=0,
                last_violation=None,
            ),
            PolicyConstraint(
                policy_id="pol_003",
                policy_type=GovernancePolicy.MAX_LEVERAGE,
                threshold=2.0,
                enabled=True,
                violations=0,
                last_violation=None,
            ),
            PolicyConstraint(
                policy_id="pol_004",
                policy_type=GovernancePolicy.REQUIRED_EXPLAINABILITY,
                threshold=1.0,
                enabled=True,
                violations=0,
                last_violation=None,
            ),
        ]
    
    def add_policy(self, policy_type: GovernancePolicy,
                  threshold: float,
                  enabled: bool = True) -> PolicyConstraint:
        policy_id = hashlib.sha256(
            f"{policy_type.value}{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:16]
        
        policy = PolicyConstraint(
            policy_id=policy_id,
            policy_type=policy_type,
            threshold=threshold,
            enabled=enabled,
            violations=0,
            last_violation=None,
        )
        
        self._policies.append(policy)
        return policy
    
    def validate_decision(self, ai_decision: Dict[str, Any],
                         explanation: Optional[str] = None) -> GovernanceDecision:
        decision_id = hashlib.sha256(
            f"{ai_decision}{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:16]
        
        violated_policies = []
        
        for policy in self._policies:
            if not policy.enabled:
                continue
            
            if not self._check_policy_compliance(policy, ai_decision):
                violated_policies.append(policy.policy_id)
                policy.violations += 1
                policy.last_violation = datetime.now(timezone.utc).isoformat()
                self._violation_count += 1
        
        policy_check_passed = len(violated_policies) == 0
        
        explanation_required = any(
            p.policy_type == GovernancePolicy.REQUIRED_EXPLAINABILITY
            for p in self._policies if p.enabled
        )
        
        decision = GovernanceDecision(
            decision_id=decision_id,
            ai_decision=ai_decision,
            policy_check_passed=policy_check_passed,
            violated_policies=violated_policies,
            human_override_available=not policy_check_passed,
            explanation_required=explanation_required and explanation is None,
            timestamp=datetime.now(timezone.utc).isoformat(),
            approved=policy_check_passed and (explanation is not None or not explanation_required),
        )
        
        self._decisions.append(decision)
        return decision
    
    def _check_policy_compliance(self, policy: PolicyConstraint,
                                decision: Dict[str, Any]) -> bool:
        if policy.policy_type == GovernancePolicy.MAX_POSITION_SIZE:
            position_size = decision.get('position_size_pct', 0)
            return position_size <= policy.threshold
        
        elif policy.policy_type == GovernancePolicy.MAX_DRAWDOWN:
            drawdown = decision.get('current_drawdown', 0)
            return drawdown <= policy.threshold
        
        elif policy.policy_type == GovernancePolicy.MAX_LEVERAGE:
            leverage = decision.get('leverage', 1)
            return leverage <= policy.threshold
        
        elif policy.policy_type == GovernancePolicy.RESTRICTED_ASSETS:
            asset = decision.get('asset', '')
            restricted = decision.get('restricted_assets', [])
            return asset not in restricted
        
        return True
    
    def activate_human_override(self) -> None:
        self._human_override_active = True
        print("[GOVERNANCE] Human override ACTIVATED")
    
    def deactivate_human_override(self) -> None:
        self._human_override_active = False
        print("[GOVERNANCE] Human override DEACTIVATED")
    
    def override_decision(self, decision_id: str,
                         override_action: str,
                         human_operator: str) -> bool:
        for decision in self._decisions:
            if decision.decision_id == decision_id:
                decision.approved = (override_action == "approve")
                print(f"[GOVERNANCE] Human override by {human_operator}: {override_action}")
                return True
        return False
    
    def get_governance_report(self) -> Dict[str, Any]:
        return {
            'total_policies': len(self._policies),
            'active_policies': sum(1 for p in self._policies if p.enabled),
            'total_violations': self._violation_count,
            'total_decisions': len(self._decisions),
            'approved_decisions': sum(1 for d in self._decisions if d.approved),
            'human_override_active': self._human_override_active,
            'policy_violations': [
                {
                    'policy_id': p.policy_id,
                    'type': p.policy_type.value,
                    'violations': p.violations,
                }
                for p in self._policies if p.violations > 0
            ],
        }


_ai_governance: Optional[AIGovernanceFramework] = None

def get_ai_governance() -> AIGovernanceFramework:
    global _ai_governance
    if _ai_governance is None:
        _ai_governance = AIGovernanceFramework()
    return _ai_governance
