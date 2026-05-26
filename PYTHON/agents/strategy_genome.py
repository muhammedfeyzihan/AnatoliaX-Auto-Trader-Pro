"""
agents/strategy_genome.py — Strategy Genome System (Phase 4)
Module 15 from anatoliax_prompt_v6.txt

Features:
  - Genome G = {parameters, indicator_weights, entry_logic_hash, exit_logic_hash, regime_fitness}
  - Mutation: theta' = theta + N(0, sigma_mutate)
  - Lineage: tree parent->child with generation number
  - Survival score: S = w1*Sharpe_regime + w2*Calmar_regime - w3*max_drawdown
  - Promote: if S > S_threshold and paper_trades > N_min, promote to live
  - Archive: if S < S_archive, move to archive with metadata
"""

import random
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from collections import defaultdict


@dataclass
class StrategyGenome:
    genome_id: str
    generation: int = 0
    parent_id: Optional[str] = None
    parameters: Dict[str, float] = field(default_factory=dict)
    indicator_weights: Dict[str, float] = field(default_factory=dict)
    entry_logic_hash: str = ""
    exit_logic_hash: str = ""
    regime_fitness: Dict[str, float] = field(default_factory=dict)
    status: str = "paper"  # paper, live, archive
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class StrategyGenomeSystem:
    """
    Evolutionary strategy genome system with mutation, lineage, and promotion.
    """

    def __init__(
        self,
        mutate_sigma: float = 0.1,
        survival_threshold: float = 1.0,
        archive_threshold: float = -1.0,
        min_paper_trades: int = 100,
    ):
        self.mutate_sigma = mutate_sigma
        self.survival_threshold = survival_threshold
        self.archive_threshold = archive_threshold
        self.min_paper_trades = min_paper_trades
        self._genomes: Dict[str, StrategyGenome] = {}
        self._lineage: Dict[str, List[str]] = defaultdict(list)  # parent -> children
        self._scores: Dict[str, float] = {}

    def create_genome(
        self,
        genome_id: str,
        parent_id: Optional[str] = None,
        parameters: Optional[Dict[str, float]] = None,
        indicator_weights: Optional[Dict[str, float]] = None,
    ) -> StrategyGenome:
        gen = 0
        if parent_id and parent_id in self._genomes:
            gen = self._genomes[parent_id].generation + 1

        genome = StrategyGenome(
            genome_id=genome_id,
            generation=gen,
            parent_id=parent_id,
            parameters=parameters or {},
            indicator_weights=indicator_weights or {},
        )
        if parent_id:
            self._lineage[parent_id].append(genome_id)
        self._genomes[genome_id] = genome
        return genome

    def mutate(self, genome_id: str) -> StrategyGenome:
        parent = self._genomes.get(genome_id)
        if not parent:
            raise ValueError("Genome not found")

        new_params = {
            k: max(0.0, v + random.gauss(0, self.mutate_sigma))
            for k, v in parent.parameters.items()
        }
        child = self.create_genome(
            genome_id=f"{genome_id}_gen{parent.generation+1}_{random.randint(1000,9999)}",
            parent_id=genome_id,
            parameters=new_params,
            indicator_weights=parent.indicator_weights.copy(),
        )
        return child

    def score_genome(self, genome_id: str, sharpe: float, calmar: float, max_dd: float, regime: str, paper_trades: int):
        w1, w2, w3 = 0.5, 0.3, 0.2
        score = w1 * sharpe + w2 * calmar - w3 * max_dd
        self._scores[genome_id] = score
        genome = self._genomes.get(genome_id)
        if genome:
            genome.regime_fitness[regime] = score
            if score >= self.survival_threshold and paper_trades >= self.min_paper_trades and genome.status == "paper":
                genome.status = "live"
            elif score <= self.archive_threshold:
                genome.status = "archive"

    def get_top_genomes(self, n: int = 5) -> List[str]:
        sorted_genomes = sorted(self._scores.items(), key=lambda x: x[1], reverse=True)
        return [g[0] for g in sorted_genomes[:n]]
