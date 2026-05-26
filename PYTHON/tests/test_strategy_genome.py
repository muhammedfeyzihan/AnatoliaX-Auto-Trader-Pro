import pytest
from agents.strategy_genome import StrategyGenomeSystem, StrategyGenome


def test_create_genome():
    sys = StrategyGenomeSystem()
    g = sys.create_genome("gen1", parameters={"ema_fast": 12})
    assert g.genome_id == "gen1"
    assert g.generation == 0
    assert g.status == "paper"


def test_create_child_genome():
    sys = StrategyGenomeSystem()
    parent = sys.create_genome("parent1", parameters={"ema_fast": 12})
    child = sys.create_genome("child1", parent_id="parent1", parameters={"ema_fast": 14})
    assert child.parent_id == "parent1"
    assert child.generation == 1


def test_mutate():
    sys = StrategyGenomeSystem()
    sys.create_genome("gen1", parameters={"ema_fast": 12.0})
    child = sys.mutate("gen1")
    assert child.parent_id == "gen1"
    assert child.generation == 1
    assert "ema_fast" in child.parameters


def test_score_genome_promotion():
    sys = StrategyGenomeSystem(survival_threshold=1.0, min_paper_trades=10)
    sys.create_genome("gen1")
    sys.score_genome("gen1", sharpe=2.0, calmar=1.5, max_dd=0.05, regime="bull", paper_trades=20)
    assert sys._genomes["gen1"].status == "live"


def test_score_genome_archive():
    sys = StrategyGenomeSystem(archive_threshold=-0.5)
    sys.create_genome("gen1")
    sys.score_genome("gen1", sharpe=-1.0, calmar=-1.0, max_dd=0.50, regime="bear", paper_trades=5)
    assert sys._genomes["gen1"].status == "archive"


def test_get_top_genomes():
    sys = StrategyGenomeSystem()
    sys.create_genome("gen1")
    sys.create_genome("gen2")
    sys.score_genome("gen1", sharpe=2.0, calmar=1.0, max_dd=0.1, regime="bull", paper_trades=10)
    sys.score_genome("gen2", sharpe=1.0, calmar=0.5, max_dd=0.2, regime="bull", paper_trades=10)
    top = sys.get_top_genomes(n=2)
    assert top[0] == "gen1"
