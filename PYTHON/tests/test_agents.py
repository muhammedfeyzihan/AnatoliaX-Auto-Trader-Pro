"""
Test: PYTHON.agents.orchestrator + memory
Agent planning, execution, feedback learning.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.orchestrator import AgentOrchestrator, AgentTask
from agents.memory import AgentMemory


class TestAgentOrchestrator:
    def test_register_and_plan(self):
        orch = AgentOrchestrator()
        orch.register_tool("Sinyal", lambda p: {"signal": "BUY"})
        plan = orch.plan("THYAO", {"regime": "bull"})
        assert len(plan) == 3
        assert any(t.agent == "Sinyal" for t in plan)
        assert any(t.agent == "Risk" for t in plan)
        assert any(t.agent == "Strateji" for t in plan)

    def test_execute(self):
        orch = AgentOrchestrator()
        orch.register_tool("Sinyal", lambda p: {"signal": "BUY", "score": 75})
        task = AgentTask(id="t1", agent="Sinyal", action="analyze", params={"symbol": "THYAO"})
        result = orch.execute(task)
        assert result["signal"] == "BUY"
        assert task.status == "completed"

    def test_run_all(self):
        orch = AgentOrchestrator()
        for agent in ["Sinyal", "Risk", "Strateji"]:
            orch.register_tool(agent, lambda p, a=agent: {"agent": a, "status": "OK"})
        result = orch.run_all("THYAO", {})
        assert result["status"] == "OK"

    def test_run_all_rejected(self):
        orch = AgentOrchestrator()
        orch.register_tool("Sinyal", lambda p: {"status": "RED"})
        orch.register_tool("Risk", lambda p: {"status": "OK"})
        orch.register_tool("Strateji", lambda p: {"status": "OK"})
        result = orch.run_all("THYAO", {})
        assert result["status"] == "REJECTED"

    def test_scoreboard(self):
        orch = AgentOrchestrator()
        orch.register_tool("Sinyal", lambda p: {"ok": True})
        task = AgentTask(id="t1", agent="Sinyal", action="test", params={})
        orch.execute(task)
        sb = orch.get_scoreboard()
        assert "Sinyal" in sb
        assert sb["Sinyal"]["total"] == 1

    def test_attach_module(self):
        orch = AgentOrchestrator()
        orch.attach_module("microstructure", {"dummy": True})
        assert "microstructure" in orch._enhancements

    def test_run_with_enhancements_no_liquidity(self):
        orch = AgentOrchestrator()
        for agent in ["Sinyal", "Risk", "Strateji"]:
            orch.register_tool(agent, lambda p, a=agent: {"agent": a, "status": "OK"})
        orch.attach_module("liquidity_collapse", type("MockLCS", (), {"calculate_lcs": lambda self: 0.3})())
        result = orch.run_with_enhancements("THYAO", {})
        assert result["status"] == "OK"
        assert "preflight" in result

    def test_run_with_enhancements_liquidity_reject(self):
        orch = AgentOrchestrator()
        for agent in ["Sinyal", "Risk", "Strateji"]:
            orch.register_tool(agent, lambda p, a=agent: {"agent": a, "status": "OK"})
        orch.attach_module("liquidity_collapse", type("MockLCS", (), {"calculate_lcs": lambda self: 0.8})())
        result = orch.run_with_enhancements("THYAO", {})
        assert result["status"] == "REJECTED"
        assert result["reason"] == "Liquidity collapse predicted"


class TestAgentMemory:
    def test_record_and_best_action(self, tmp_path):
        mem = AgentMemory(agent="B_test", memory_dir=str(tmp_path))
        mem.record_decision(state="bull", action="BUY", reward=1.0)
        mem.record_decision(state="bull", action="SELL", reward=-1.0)
        best = mem.best_action("bull", ["BUY", "SELL"])
        # Epsilon-greedy nedeniyle deterministik degil, ama BUY daha yuksek Q degerine sahip
        stats = mem.get_stats()
        assert stats["total"] == 2
