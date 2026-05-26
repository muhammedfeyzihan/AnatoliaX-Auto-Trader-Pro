"""
agent_council.py — Agent Council Meeting & Consensus System

Inspired by Ruflo's "Slack for Agents" + Queen-led hierarchy + Byzantine consensus.

Agents hold structured meetings to vote on signals. Each agent has:
- A persona (personality, risk tolerance, manipulation sensitivity)
- A vote (BUY, SELL, WAIT, BLOCK)
- A trust score (dynamic, updated by outcomes)

Consensus protocols:
- SIMPLE_MAJORITY: 50%+1
- SUPER_MAJORITY: 66%+
- BYZANTINE: Tolerates up to f faulty agents (2f+1 total)
- UNANIMOUS: 100%

The Queen agent (Strategy/Leader) breaks ties and has veto power.

Usage:
    from agents.agent_council import AgentCouncil
    council = AgentCouncil()
    result = council.hold_meeting(symbol="THYAO", signal={...}, df=df)
    print(result.decision, result.votes)
"""

import time
import hashlib
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from agents.agent_personas import AgentPersonaRegistry, Role, Personality
from agents.manipulation_detector import ManipulationDetector, ManipulationResult
from common.platform_optimizer import get_optimal_workers


class Vote(Enum):
    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"
    BLOCK = "BLOCK"


class ConsensusType(Enum):
    SIMPLE_MAJORITY = "SIMPLE_MAJORITY"
    SUPER_MAJORITY = "SUPER_MAJORITY"
    BYZANTINE = "BYZANTINE"
    UNANIMOUS = "UNANIMOUS"


@dataclass
class AgentVote:
    agent_id: str
    vote: Vote
    confidence: float
    reason: str
    trust_score: float = 1.0

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "vote": self.vote.value,
            "confidence": round(self.confidence, 1),
            "reason": self.reason,
            "trust_score": round(self.trust_score, 3),
        }


@dataclass
class MeetingResult:
    symbol: str
    decision: Vote
    confidence: float
    consensus_reached: bool
    votes: List[AgentVote] = field(default_factory=list)
    manipulation_alert: Optional[ManipulationResult] = None
    minutes: str = ""
    checksum: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "decision": self.decision.value,
            "confidence": round(self.confidence, 1),
            "consensus_reached": self.consensus_reached,
            "votes": [v.to_dict() for v in self.votes],
            "manipulation_alert": self.manipulation_alert.__dict__ if self.manipulation_alert else None,
            "minutes": self.minutes,
            "checksum": self.checksum,
            "timestamp": self.timestamp,
        }


class AgentCouncil:
    """
    Agent Council Meeting System.

    Kural K264: Council toplantisi EN AZ 3 ajan ile yapilir.
    Kural K265: Manipulasyon skoru > 70 olan sembolde council otomatik BLOCK verir.
    Kural K266: Queen ajan (Strateji) tie-breaker'dir ve veto hakkina sahiptir.
    Kural K267: Trust score < 0.5 olan ajanin oyu %50 agirlikli sayilir.
    Kural K275: Varsayilan olarak TUM tanimli ajanlar aktiftir (dinamik sayi).
    Kural K276: Her islem oncesi tum ajanlar AYNI ANDA toplanir (parallel council).
    Kural K277: Toplam karar suresi < 500ms olmalidir (paralel calisma).
    Kural K278: Ajan sayisi = min(CPU cekirdek sayisi, mevcut ajan sayisi).
    Kural K279: Cross-platform: Windows/Linux/Mac ThreadPoolExecutor kullanir.
    """

    def __init__(
        self,
        consensus: ConsensusType = ConsensusType.SUPER_MAJORITY,
        max_agents: Optional[int] = None,
        parallel: bool = True,
        max_meeting_ms: float = 500.0,
        staged: bool = False,
    ):
        self.personas = AgentPersonaRegistry()
        self.manip_detector = ManipulationDetector()
        self.consensus = consensus
        # K278: Dynamic agent count based on CPU cores and available personas
        available = len(self.personas.list_agents())
        optimal = get_optimal_workers(max_workers=max_agents)
        self.max_agents = min(optimal, available)
        self.parallel = parallel
        self.max_meeting_ms = max_meeting_ms
        self.staged = staged
        self._trust_scores: Dict[str, float] = defaultdict(lambda: 1.0)
        self._meeting_history: List[MeetingResult] = []
        self._executor = ThreadPoolExecutor(max_workers=self.max_agents) if parallel else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def hold_meeting(
        self,
        symbol: str,
        signal: dict,
        df: Optional[pd.DataFrame] = None,
        macro: Optional[dict] = None,
        news_sentiment: Optional[dict] = None,
    ) -> MeetingResult:
        """
        Convene all agents for a structured meeting.
        K277: Toplam karar suresi < 500ms (paralel calisma).

        signal: {"side": "BUY", "confidence": 75, "setup": "MOMENTUM", "entry": 105.0, "sl": 100.0}
        """
        start_ts = time.time()

        # 1. Manipulation check first
        manip_alert = None
        if df is not None and len(df) >= 20:
            manip_alert = self.manip_detector.analyze(df, symbol=symbol)
            if manip_alert.is_manipulated and manip_alert.score >= 70:
                pass

        # 2. Gather agent votes (PARALLEL for speed)
        if self.staged and self.parallel and self._executor:
            votes = self._gather_votes_staged(symbol, signal, manip_alert, macro, news_sentiment)
        elif self.parallel and self._executor:
            votes = self._gather_votes_parallel(symbol, signal, manip_alert, macro, news_sentiment)
        else:
            votes = self._gather_votes(symbol, signal, manip_alert, macro, news_sentiment)

        # 3. Apply trust-weighting
        weighted_votes = self._apply_trust(votes)

        # 4. Determine consensus
        decision, confidence, reached = self._determine_consensus(weighted_votes)

        # 5. Queen tie-break / veto
        queen_vote = next((v for v in weighted_votes if v.agent_id == "strategy"), None)

        if manip_alert and manip_alert.is_manipulated and manip_alert.score >= 70:
            decision = Vote.BLOCK
            confidence = 100.0
            reached = True
            if queen_vote:
                queen_vote.vote = Vote.BLOCK
                queen_vote.reason = f"Manipulasyon tespiti: {manip_alert.pattern.value} ({manip_alert.score:.0f})"

        if confidence < 60 and queen_vote:
            decision = queen_vote.vote
            confidence = queen_vote.confidence

        # 6. Generate minutes
        minutes = self._generate_minutes(symbol, weighted_votes, decision, manip_alert)

        elapsed_ms = (time.time() - start_ts) * 1000.0

        result = MeetingResult(
            symbol=symbol,
            decision=decision,
            confidence=confidence,
            consensus_reached=reached,
            votes=weighted_votes,
            manipulation_alert=manip_alert,
            minutes=minutes + f"\nMeeting duration: {elapsed_ms:.1f}ms",
        )
        result.checksum = self._checksum(result)
        self._meeting_history.append(result)
        return result

    def update_trust(self, agent_id: str, outcome: float):
        """
        Update trust score after trade outcome.
        outcome: PnL as % of capital (positive = good, negative = bad)
        """
        current = self._trust_scores[agent_id]
        # Exponential moving average of trust
        alpha = 0.3
        if outcome > 0:
            self._trust_scores[agent_id] = min(2.0, current + alpha * outcome)
        else:
            self._trust_scores[agent_id] = max(0.0, current + alpha * outcome)

    def get_trust_scores(self) -> Dict[str, float]:
        return dict(self._trust_scores)

    def get_meeting_history(self, symbol: Optional[str] = None, limit: int = 100) -> List[MeetingResult]:
        results = list(self._meeting_history)
        if symbol:
            results = [r for r in results if r.symbol == symbol.upper()]
        return results[-limit:]

    # ------------------------------------------------------------------
    # Internal: Voting logic
    # ------------------------------------------------------------------
    def _gather_votes(
        self,
        symbol: str,
        signal: dict,
        manip: Optional[ManipulationResult],
        macro: Optional[dict],
        news_sentiment: Optional[dict],
    ) -> List[AgentVote]:
        votes = []
        signal_conf = signal.get("confidence", 0.0)
        signal_side = signal.get("side", "BUY")
        manip_score = manip.score if manip else 0.0
        manip_pattern = manip.pattern if manip else None

        # K275/K278: All available agents participate in council for maximum speed
        for agent_id in self.personas.list_agents():
            persona = self.personas.get(agent_id)
            if not persona:
                continue

            # Base bias from persona
            bias = persona.vote_bias(signal_conf, manip_score / 100.0)

            # Role-specific overrides
            vote = Vote.WAIT
            reason = "Bekleme"
            confidence = 50.0

            if persona.role == Role.SIGNAL:
                # Signal agent: votes with the signal if bias allows
                if bias > 0.2:
                    vote = Vote.BUY if signal_side == "BUY" else Vote.SELL
                    confidence = signal_conf
                    reason = f"Sinyal onayli: {signal.get('setup', '')}"
                elif bias < -0.3:
                    vote = Vote.BLOCK
                    reason = "Sinyal guvensiz"
                    confidence = 70.0
                else:
                    vote = Vote.WAIT
                    reason = "Belirsizlik yuksek"

            elif persona.role == Role.RISK:
                # Risk agent: blocks if any red flag
                if manip_score >= 50:
                    vote = Vote.BLOCK
                    confidence = min(50 + manip_score / 2, 95)
                    reason = f"Risk: {manip_pattern.value if manip_pattern else 'manipulasyon'} {manip_score:.0f}"
                elif signal_conf < persona.confidence_threshold:
                    vote = Vote.BLOCK
                    confidence = 80.0
                    reason = f"Confidence {signal_conf:.0f} < {persona.confidence_threshold:.0f}"
                elif bias > 0.1:
                    vote = Vote.BUY if signal_side == "BUY" else Vote.SELL
                    confidence = signal_conf * 0.9
                    reason = "Risk kabul edilebilir"
                else:
                    vote = Vote.WAIT
                    reason = "Risk analizi devam ediyor"

            elif persona.role == Role.STRATEGY:
                # Strategy agent: Queen, makes balanced decision
                if manip_score >= 70:
                    vote = Vote.BLOCK
                    confidence = 95.0
                    reason = "Manipulasyon tespiti — veto"
                elif signal_conf >= 70 and bias > 0.3:
                    vote = Vote.BUY if signal_side == "BUY" else Vote.SELL
                    confidence = signal_conf
                    reason = f"Strateji onayi: {signal.get('setup', '')}"
                elif signal_conf >= 50 and bias > 0.0:
                    vote = Vote.WAIT
                    confidence = signal_conf
                    reason = "Bekle-gor, daha fazla veri gerekli"
                else:
                    vote = Vote.BLOCK
                    confidence = 80.0
                    reason = "Strateji reddediyor"

            elif persona.role == Role.NEWS:
                # News agent: uses sentiment and macro
                sentiment_bias = news_sentiment.get("score", 0.0) if news_sentiment else 0.0
                if abs(sentiment_bias) > 0.6:
                    vote = Vote.BUY if sentiment_bias > 0 else Vote.SELL
                    confidence = abs(sentiment_bias) * 100
                    reason = f"Haber sentiment: {sentiment_bias:.2f}"
                elif manip_score > 30:
                    vote = Vote.BLOCK
                    reason = "Haber manipulasyonu suphesi"
                    confidence = 60.0
                else:
                    vote = Vote.WAIT
                    reason = "Haber etkisi notr"

            elif persona.role == Role.BLACK_SWAN:
                # Black swan: paranoid, blocks easily
                if manip_score > 20 or signal_conf < 80:
                    vote = Vote.BLOCK
                    confidence = 90.0
                    reason = "Kara kugu kapisi — risk yuksek"
                else:
                    vote = Vote.WAIT
                    reason = "Izleme modu"

            elif persona.role == Role.EXECUTION:
                # Execution: checks feasibility
                if signal_conf >= 60 and bias >= 0.0:
                    vote = Vote.BUY if signal_side == "BUY" else Vote.SELL
                    confidence = signal_conf * 0.8
                    reason = "Icra mumkun"
                else:
                    vote = Vote.WAIT
                    reason = "Icra kosullari uygun degil"

            votes.append(AgentVote(
                agent_id=agent_id,
                vote=vote,
                confidence=confidence,
                reason=reason,
                trust_score=self._trust_scores[agent_id],
            ))

        return votes

    def _gather_votes_parallel(
        self,
        symbol: str,
        signal: dict,
        manip: Optional[ManipulationResult],
        macro: Optional[dict],
        news_sentiment: Optional[dict],
    ) -> List[AgentVote]:
        """
        K277-optimized parallel vote gathering using ThreadPoolExecutor.
        All available agents participate per K275/K278.
        """
        if not self._executor:
            return self._gather_votes(symbol, signal, manip, macro, news_sentiment)

        signal_conf = signal.get("confidence", 0.0)
        signal_side = signal.get("side", "BUY")
        manip_score = manip.score if manip else 0.0
        manip_pattern = manip.pattern if manip else None

        # K275/K278: All available agents participate in council
        futures = {}
        for agent_id in self.personas.list_agents():
            persona = self.personas.get(agent_id)
            if not persona:
                continue
            futures[self._executor.submit(
                self._compute_agent_vote,
                persona, signal_conf, signal_side, manip_score, manip_pattern,
                macro, news_sentiment, self._trust_scores[agent_id],
            )] = agent_id

        votes = []
        for future in futures:
            try:
                vote = future.result(timeout=0.3)  # 300ms max per agent (K277)
                votes.append(vote)
            except Exception:
                # Timeout or error = agent couldn't vote in time
                agent_id = futures[future]
                votes.append(AgentVote(
                    agent_id=agent_id,
                    vote=Vote.WAIT,
                    confidence=0.0,
                    reason="Timeout/Error (parallel)",
                    trust_score=self._trust_scores[agent_id],
                ))
        return votes

    def _gather_votes_staged(
        self,
        symbol: str,
        signal: dict,
        manip: Optional[ManipulationResult],
        macro: Optional[dict],
        news_sentiment: Optional[dict],
    ) -> List[AgentVote]:
        """
        Staged 3-3 council mode (K276 variant):
        Phase 1: signal + risk + news (parallel)
        Phase 2: black_swan + execution + strategy (parallel, sees Phase 1 votes)
        Total time still < 500ms.
        """
        if not self._executor:
            return self._gather_votes(symbol, signal, manip, macro, news_sentiment)

        signal_conf = signal.get("confidence", 0.0)
        signal_side = signal.get("side", "BUY")
        manip_score = manip.score if manip else 0.0
        manip_pattern = manip.pattern if manip else None

        # Phase 1: signal, risk, news
        phase1_agents = ["signal", "risk", "news"]
        phase1_futures = {}
        for agent_id in phase1_agents:
            persona = self.personas.get(agent_id)
            if not persona:
                continue
            phase1_futures[self._executor.submit(
                self._compute_agent_vote,
                persona, signal_conf, signal_side, manip_score, manip_pattern,
                macro, news_sentiment, self._trust_scores[agent_id],
            )] = agent_id

        phase1_votes = []
        for future in phase1_futures:
            try:
                vote = future.result(timeout=0.3)
                phase1_votes.append(vote)
            except Exception:
                agent_id = phase1_futures[future]
                phase1_votes.append(AgentVote(
                    agent_id=agent_id,
                    vote=Vote.WAIT,
                    confidence=0.0,
                    reason="Timeout/Error (Phase 1)",
                    trust_score=self._trust_scores[agent_id],
                ))

        # Phase 2: black_swan, execution, strategy (sees Phase 1 results)
        phase2_agents = ["black_swan", "execution", "strategy"]
        phase2_futures = {}
        for agent_id in phase2_agents:
            persona = self.personas.get(agent_id)
            if not persona:
                continue
            phase2_futures[self._executor.submit(
                self._compute_agent_vote,
                persona, signal_conf, signal_side, manip_score, manip_pattern,
                macro, news_sentiment, self._trust_scores[agent_id],
                phase1_votes,
            )] = agent_id

        phase2_votes = []
        for future in phase2_futures:
            try:
                vote = future.result(timeout=0.3)
                phase2_votes.append(vote)
            except Exception:
                agent_id = phase2_futures[future]
                phase2_votes.append(AgentVote(
                    agent_id=agent_id,
                    vote=Vote.WAIT,
                    confidence=0.0,
                    reason="Timeout/Error (Phase 2)",
                    trust_score=self._trust_scores[agent_id],
                ))

        return phase1_votes + phase2_votes

    @staticmethod
    def _compute_agent_vote(
        persona,
        signal_conf: float,
        signal_side: str,
        manip_score: float,
        manip_pattern,
        macro: Optional[dict],
        news_sentiment: Optional[dict],
        trust_score: float,
        phase1_votes: Optional[List[AgentVote]] = None,
    ) -> AgentVote:
        """Compute a single agent's vote (static for pickle-free parallel execution).
        phase1_votes: Optional Phase 1 results for staged council mode."""
        bias = persona.vote_bias(signal_conf, manip_score / 100.0)
        vote = Vote.WAIT
        reason = "Bekleme"
        confidence = 50.0

        # Helper: check Phase 1 consensus trend
        phase1_buy = 0
        phase1_block = 0
        if phase1_votes:
            phase1_buy = sum(1 for v in phase1_votes if v.vote in (Vote.BUY, Vote.SELL))
            phase1_block = sum(1 for v in phase1_votes if v.vote == Vote.BLOCK)

        # Signal Agent (includes NEWS capabilities per K275 integration)
        if persona.role == Role.SIGNAL:
            if bias > 0.2:
                vote = Vote.BUY if signal_side == "BUY" else Vote.SELL
                confidence = signal_conf
                reason = f"Sinyal onayli: {signal_side}"
            elif bias < -0.3:
                vote = Vote.BLOCK
                reason = "Sinyal guvensiz"
                confidence = 70.0
            else:
                vote = Vote.WAIT
                reason = "Belirsizlik yuksek"

        # Risk Agent (includes BLACK_SWAN capabilities per K275 integration)
        elif persona.role == Role.RISK:
            if manip_score >= 50:
                vote = Vote.BLOCK
                confidence = min(50 + manip_score / 2, 95)
                reason = f"Risk: manipulasyon {manip_score:.0f}"
            elif signal_conf < persona.confidence_threshold:
                vote = Vote.BLOCK
                confidence = 80.0
                reason = f"Confidence {signal_conf:.0f} < {persona.confidence_threshold:.0f}"
            elif bias > 0.1:
                vote = Vote.BUY if signal_side == "BUY" else Vote.SELL
                confidence = signal_conf * 0.9
                reason = "Risk kabul edilebilir"
            else:
                vote = Vote.WAIT
                reason = "Risk analizi devam ediyor"

        # Strategy Agent (Queen)
        elif persona.role == Role.STRATEGY:
            if manip_score >= 70:
                vote = Vote.BLOCK
                confidence = 95.0
                reason = "Manipulasyon tespiti — veto"
            elif signal_conf >= 70 and bias > 0.3:
                vote = Vote.BUY if signal_side == "BUY" else Vote.SELL
                confidence = signal_conf
                reason = f"Strateji onayi: {signal_side}"
            elif signal_conf >= 50 and bias > 0.0:
                vote = Vote.WAIT
                confidence = signal_conf
                reason = "Bekle-gor, daha fazla veri gerekli"
            else:
                vote = Vote.BLOCK
                confidence = 80.0
                reason = "Strateji reddediyor"

        # News Agent
        elif persona.role == Role.NEWS:
            if manip_score >= 40:
                vote = Vote.BLOCK
                confidence = 70.0
                reason = "Haber manipulasyonu suphesi"
            elif bias > 0.15:
                vote = Vote.BUY if signal_side == "BUY" else Vote.SELL
                confidence = signal_conf * 0.85
                reason = "Haber destekli"
            elif bias < -0.15:
                vote = Vote.WAIT
                confidence = 60.0
                reason = "Haber belirsizligi"
            else:
                vote = Vote.WAIT
                confidence = 50.0
                reason = "Haber etkisi notr"

        # Black Swan Agent
        elif persona.role == Role.BLACK_SWAN:
            if manip_score > 25 or signal_conf < 85 or phase1_block > 0:
                vote = Vote.BLOCK
                confidence = 90.0
                reason = "Kara kugu kapisi — risk yuksek"
            else:
                vote = Vote.WAIT
                confidence = 50.0
                reason = "Izleme modu"

        # Execution Agent
        elif persona.role == Role.EXECUTION:
            if signal_conf >= 65 and bias >= 0.0 and manip_score < 30 and phase1_buy > 0:
                vote = Vote.BUY if signal_side == "BUY" else Vote.SELL
                confidence = signal_conf * 0.8
                reason = "Icra mumkun"
            else:
                vote = Vote.WAIT
                confidence = 50.0
                reason = "Icra kosullari uygun degil"

        return AgentVote(
            agent_id=persona.name.lower(),
            vote=vote,
            confidence=confidence,
            reason=reason,
            trust_score=trust_score,
        )

    def _apply_trust(self, votes: List[AgentVote]) -> List[AgentVote]:
        """Reduce voting power of low-trust agents."""
        for v in votes:
            if v.trust_score < 0.5:
                v.confidence *= 0.5
        return votes

    def _determine_consensus(self, votes: List[AgentVote]) -> Tuple[Vote, float, bool]:
        """Return (decision, confidence, reached)."""
        if not votes:
            return Vote.WAIT, 0.0, False

        # Weighted vote counting
        counts = defaultdict(float)
        total_weight = 0.0
        for v in votes:
            weight = v.confidence * v.trust_score
            counts[v.vote] += weight
            total_weight += weight

        if total_weight <= 0:
            return Vote.WAIT, 0.0, False

        # Find winner
        winner = max(counts, key=counts.get)
        winner_weight = counts[winner]
        ratio = winner_weight / total_weight

        # Consensus thresholds
        thresholds = {
            ConsensusType.SIMPLE_MAJORITY: 0.50,
            ConsensusType.SUPER_MAJORITY: 0.66,
            ConsensusType.BYZANTINE: 0.66,  # 2f+1 simplified
            ConsensusType.UNANIMOUS: 1.0,
        }
        threshold = thresholds.get(self.consensus, 0.66)
        reached = ratio >= threshold

        confidence = ratio * 100
        return winner, confidence, reached

    def _generate_minutes(self, symbol: str, votes: List[AgentVote], decision: Vote, manip: Optional[ManipulationResult]) -> str:
        lines = [
            f"=== AGENT COUNCIL MINUTES: {symbol} ===",
            f"Time: {pd.Timestamp.now().isoformat()}",
            f"Final Decision: {decision.value}",
            "",
            "VOTES:",
        ]
        for v in votes:
            lines.append(f"  {v.agent_id:12s} -> {v.vote.value:6s} (conf={v.confidence:.0f}, trust={v.trust_score:.2f}) — {v.reason}")
        if manip and manip.is_manipulated:
            lines.append("")
            lines.append(f"MANIPULATION ALERT: {manip.pattern.value} (score={manip.score:.0f})")
            for ev in manip.evidence:
                lines.append(f"  - {ev}")
        lines.append("=== END ===")
        return "\n".join(lines)

    def _checksum(self, result: MeetingResult) -> str:
        payload = f"{result.symbol}_{result.decision.value}_{result.timestamp}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


if __name__ == "__main__":
    council = AgentCouncil(consensus=ConsensusType.SUPER_MAJORITY)

    # Normal signal
    result = council.hold_meeting(
        symbol="THYAO",
        signal={"side": "BUY", "confidence": 75, "setup": "MOMENTUM", "entry": 105.0, "sl": 100.0},
    )
    print(result.minutes)
    print(f"\nDecision: {result.decision.value}, Confidence: {result.confidence:.1f}%, Reached: {result.consensus_reached}")

    # After a win, update trust
    council.update_trust("signal", 0.02)
    print("\nTrust scores:", council.get_trust_scores())
