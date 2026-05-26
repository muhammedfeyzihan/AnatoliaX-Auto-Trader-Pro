"""
agent_personas.py — Agent Persona Definitions (MiroFish-inspired)

Each agent has a distinct personality, memory, and behavioral bias
that affects how it votes in council meetings.

Usage:
    from agents.agent_personas import AgentPersonaRegistry
    registry = AgentPersonaRegistry()
    signal_agent = registry.get("signal")
    print(signal_agent.personality)  # AGGRESSIVE
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class Personality(Enum):
    AGGRESSIVE = "AGGRESSIVE"    # High risk appetite, votes BUY quickly
    CONSERVATIVE = "CONSERVATIVE"  # Low risk, votes WAIT unless certainty > 90
    BALANCED = "BALANCED"       # Standard risk-reward analysis
    PARANOID = "PARANOID"       # Sees manipulation everywhere, votes BLOCK
    OPTIMISTIC = "OPTIMISTIC"   # Bullish bias, ignores minor red flags


class Role(Enum):
    SIGNAL = "Sinyal Ajanı"
    RISK = "Risk Ajanı"
    STRATEGY = "Strateji Ajanı"
    TELEGRAM = "Telegram Ajanı"
    NEWS = "Haber/Makro Ajanı"
    BLACK_SWAN = "Kara Kuğu Ajanı"
    EXECUTION = "İcra Ajanı"


@dataclass
class AgentPersona:
    name: str
    role: Role
    personality: Personality
    risk_tolerance: float = 0.5  # 0-1
    confidence_threshold: float = 60.0
    manipulation_sensitivity: float = 0.5  # Higher = more likely to flag manipulation
    memory_weight: float = 0.3  # How much past outcomes affect current vote
    social_influence: float = 0.5  # How much peer votes affect this agent
    description: str = ""

    def vote_bias(self, signal_confidence: float, manipulation_risk: float) -> float:
        """
        Returns a bias score (-1 to +1) affecting the vote.
        Positive = more likely to approve.
        """
        base = (signal_confidence - self.confidence_threshold) / 100.0
        # Manipulation sensitivity reduces approval
        base -= manipulation_risk * self.manipulation_sensitivity
        # Personality modifiers
        if self.personality == Personality.AGGRESSIVE:
            base += 0.2
        elif self.personality == Personality.CONSERVATIVE:
            base -= 0.2
        elif self.personality == Personality.PARANOID:
            base -= 0.4
        elif self.personality == Personality.OPTIMISTIC:
            base += 0.1
        return max(-1.0, min(1.0, base))


class AgentPersonaRegistry:
    """
    Registry of all agent personas. Inspired by MiroFish swarm personas.
    """

    PERSONAS: Dict[str, AgentPersona] = {
        "signal": AgentPersona(
            name="Sinyal",
            role=Role.SIGNAL,
            personality=Personality.OPTIMISTIC,
            risk_tolerance=0.7,
            confidence_threshold=55.0,
            manipulation_sensitivity=0.3,
            memory_weight=0.2,
            social_influence=0.4,
            description="Teknik analiz ve haberleri takip eder. Genellikle erken sinyal üretir.",
        ),
        "risk": AgentPersona(
            name="Risk",
            role=Role.RISK,
            personality=Personality.PARANOID,
            risk_tolerance=0.2,
            confidence_threshold=80.0,
            manipulation_sensitivity=0.9,
            memory_weight=0.5,
            social_influence=0.2,
            description="Tüm risk kapılarını kontrol eder. Şüpheci doğasıyla manipülasyonları ilk o fark eder.",
        ),
        "strategy": AgentPersona(
            name="Strateji",
            role=Role.STRATEGY,
            personality=Personality.BALANCED,
            risk_tolerance=0.5,
            confidence_threshold=65.0,
            manipulation_sensitivity=0.5,
            memory_weight=0.4,
            social_influence=0.6,
            description="Nihai kararı verir. Sinyal ve Risk ajanlarının görüşlerini dengeler.",
        ),
        "news": AgentPersona(
            name="Haber",
            role=Role.NEWS,
            personality=Personality.CONSERVATIVE,
            risk_tolerance=0.4,
            confidence_threshold=70.0,
            manipulation_sensitivity=0.7,
            memory_weight=0.3,
            social_influence=0.5,
            description="Makro veri ve haber akışını izler. Manipülatif haberleri tespit eder.",
        ),
        "black_swan": AgentPersona(
            name="Kara Kuğu",
            role=Role.BLACK_SWAN,
            personality=Personality.PARANOID,
            risk_tolerance=0.0,
            confidence_threshold=95.0,
            manipulation_sensitivity=1.0,
            memory_weight=0.6,
            social_influence=0.1,
            description="Aşırı senaryoları ve piyasa çöküşlerini öngörür. 'Hayır' demekte tereddüt etmez.",
        ),
        "execution": AgentPersona(
            name="İcra",
            role=Role.EXECUTION,
            personality=Personality.BALANCED,
            risk_tolerance=0.4,
            confidence_threshold=75.0,
            manipulation_sensitivity=0.6,
            memory_weight=0.2,
            social_influence=0.3,
            description="Emir yönetimi ve slippage kontrolünden sorumludur.",
        ),
    }

    def __init__(self):
        self._personas = dict(self.PERSONAS)

    def get(self, agent_id: str) -> Optional[AgentPersona]:
        return self._personas.get(agent_id)
    
    def get_persona(self, name: str) -> Optional[AgentPersona]:
        """Get persona by name (alias for get)."""
        return self._personas.get(name.lower())

    def list_agents(self) -> List[str]:
        return list(self._personas.keys())

    def add_persona(self, persona: AgentPersona):
        self._personas[persona.name.lower()] = persona

    def to_dict(self) -> dict:
        return {
            k: {
                "name": v.name,
                "role": v.role.value,
                "personality": v.personality.value,
                "risk_tolerance": v.risk_tolerance,
                "confidence_threshold": v.confidence_threshold,
                "manipulation_sensitivity": v.manipulation_sensitivity,
            }
            for k, v in self._personas.items()
        }


if __name__ == "__main__":
    reg = AgentPersonaRegistry()
    for aid in reg.list_agents():
        p = reg.get(aid)
        print(f"{p.name}: {p.personality.value} (risk={p.risk_tolerance}, manip_sens={p.manipulation_sensitivity})")
        print(f"  Bias @ 70 conf, 0.2 manip: {p.vote_bias(70.0, 0.2):.2f}")
