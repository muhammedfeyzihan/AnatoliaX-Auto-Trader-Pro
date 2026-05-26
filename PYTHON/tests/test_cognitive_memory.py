import pytest
import os
from agents.cognitive_memory import (
    CognitiveMemoryLayer,
    EpisodicMemory,
    SemanticMemory,
    StrategicMemory,
)


@pytest.fixture
def mem(tmp_path):
    db = str(tmp_path / "cognitive_memory.db")
    return CognitiveMemoryLayer(db_path=db, working_capacity=5, episodic_capacity=10)


def test_add_to_working(mem):
    mem.add_to_working({"key": "value"})
    assert len(mem.get_working()) == 1


def test_working_capacity(mem):
    for i in range(10):
        mem.add_to_working({"i": i})
    assert len(mem.get_working()) == 5


def test_add_episode(mem):
    ep = EpisodicMemory(
        context="bull market",
        action="buy",
        outcome="profit",
        emotion="euphoria",
        symbol="THYAO",
        pnl=0.05,
    )
    mem.add_episode(ep)
    assert len(mem.episodic) == 1


def test_retrieve_episodes(mem):
    ep = EpisodicMemory(
        context="bull market",
        action="buy",
        outcome="profit",
        emotion="euphoria",
        symbol="THYAO",
        pnl=0.05,
    )
    mem.add_episode(ep)
    rows = mem.retrieve_episodes("bull", limit=5)
    assert len(rows) >= 1


def test_semantic_memory(mem):
    sm = SemanticMemory(
        concept="inflation",
        relation="causes",
        target="rate_hike",
        weight=0.8,
    )
    mem.add_semantic(sm)
    results = mem.query_semantic("inflation")
    assert len(results) >= 1
    assert results[0].target == "rate_hike"


def test_strategic_memory(mem):
    sm = StrategicMemory(
        goal="outperform_bist",
        plan_steps=["screen", "backtest", "deploy"],
        lessons_learned=["avoid_illiquid"],
    )
    mem.add_strategic(sm)
    summary = mem.get_strategic_summary()
    assert summary["total_lessons"] == 1
    assert "outperform_bist" in summary["goals"]


def test_compact(mem):
    for i in range(10):
        mem.add_episode(
            EpisodicMemory(
                context="bull market",
                action="buy",
                outcome="profit",
                emotion="neutral",
            )
        )
    mem.compact()
    # After compaction, semantic memories should exist for frequent patterns
    semantic = mem.query_semantic("bull market")
    assert len(semantic) >= 1
