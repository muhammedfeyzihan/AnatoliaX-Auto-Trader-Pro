"""
consensus_engine.py — Byzantine Consensus for Agent Voting

Inspired by Ruflo's swarm coordination (Raft, Byzantine, Gossip).
Agents vote on decisions; Byzantine agents (low trust) are filtered out.
Final decision requires weighted quorum based on trust scores.

Usage:
    from manipulation.consensus_engine import ByzantineConsensus
    consensus = ByzantineConsensus()
    consensus.vote(agent="signal", decision="BUY", symbol="THYAO", confidence=75)
    consensus.vote(agent="risk", decision="BUY", symbol="THYAO", confidence=80)
    consensus.vote(agent="strategy", decision="BUY", symbol="THYAO", confidence=70)
    result = consensus.resolve("THYAO")
    # result: {"decision": "BUY", "quorum": 0.85, "consensus": True}
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta


@dataclass
class Vote:
    agent_id: str
    decision: str  # BUY, SELL, HOLD, RED
    confidence: float  # 0-100
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    symbol: str = ""


class ByzantineConsensus:
    """
    Weighted Byzantine consensus engine.
    - Each agent casts a vote with confidence.
    - Weights are derived from AgentTrustScorer.
    - Byzantine agents (trust < threshold) are ignored.
    - Decision passes if weighted quorum >= min_quorum.
    """

    def __init__(
        self,
        min_quorum: float = 0.67,
        byzantine_threshold: float = 50.0,
        vote_ttl_seconds: float = 300.0,
    ):
        self.min_quorum = min_quorum
        self.byzantine_threshold = byzantine_threshold
        self.vote_ttl = vote_ttl_seconds
        self._votes: Dict[str, List[Vote]] = {}  # symbol -> list of votes

    def vote(self, agent_id: str, decision: str, symbol: str, confidence: float,
             trust_scorer: Optional["AgentTrustScorer"] = None):
        """Record an agent vote."""
        # Check if agent is Byzantine
        if trust_scorer and trust_scorer.is_byzantine(agent_id):
            return  # Ignore Byzantine agents

        v = Vote(agent_id=agent_id, decision=decision.upper(), confidence=confidence, symbol=symbol.upper())
        self._votes.setdefault(symbol.upper(), []).append(v)

    def resolve(self, symbol: str, trust_scorer: Optional["AgentTrustScorer"] = None) -> dict:
        """
        Resolve consensus for a symbol.
        Returns: {"decision": str, "quorum": float, "consensus": bool, "details": dict}
        """
        symbol = symbol.upper()
        votes = self._get_valid_votes(symbol)
        if not votes:
            return {"decision": "NO_VOTE", "quorum": 0.0, "consensus": False, "details": {}}

        # Weighted vote counting
        weights: Dict[str, float] = {}
        total_weight = 0.0
        for v in votes:
            w = 1.0
            if trust_scorer:
                w = trust_scorer.get_trust(v.agent_id) / 100.0
            weights[v.decision] = weights.get(v.decision, 0.0) + (w * v.confidence / 100.0)
            total_weight += w

        if total_weight <= 0:
            return {"decision": "NO_VOTE", "quorum": 0.0, "consensus": False, "details": {}}

        # Find dominant decision
        best_decision = max(weights, key=weights.get)
        best_weight = weights[best_decision]
        quorum = best_weight / total_weight

        consensus = quorum >= self.min_quorum

        # Detail per agent
        details = {}
        for v in votes:
            details[v.agent_id] = {
                "decision": v.decision,
                "confidence": v.confidence,
                "weight": trust_scorer.get_trust(v.agent_id) / 100.0 if trust_scorer else 1.0,
            }

        return {
            "decision": best_decision,
            "quorum": round(quorum, 3),
            "consensus": consensus,
            "details": details,
            "total_agents": len(votes),
        }

    def _get_valid_votes(self, symbol: str) -> List[Vote]:
        """Filter out expired votes."""
        all_votes = self._votes.get(symbol, [])
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.vote_ttl)
        valid = []
        for v in all_votes:
            try:
                ts = datetime.fromisoformat(v.timestamp)
                if ts >= cutoff:
                    valid.append(v)
            except Exception:
                continue
        return valid

    def clear_symbol(self, symbol: str):
        """Clear votes for a symbol after resolution."""
        self._votes.pop(symbol.upper(), None)

    def get_pending_symbols(self) -> List[str]:
        return list(self._votes.keys())
