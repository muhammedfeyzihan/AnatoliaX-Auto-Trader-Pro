"""
Test: PYTHON.agents.langgraph_workflow
AgentWorkflow: state routing, fallback, checkpoint.
"""
import pytest
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.langgraph_workflow import AgentWorkflow, AgentState, LANGGRAPH_AVAILABLE


class TestAgentWorkflow:
    def test_init_fallback(self):
        wf = AgentWorkflow()
        assert wf.sinyal_tool is not None
        assert wf.risk_tool is not None
        assert wf.strateji_tool is not None

    def test_run_returns_dict(self):
        wf = AgentWorkflow()
        result = wf.run(symbol="THYAO", context={"makro": "BOGA"})
        assert isinstance(result, dict)
        assert "final_decision" in result
        assert "logs" in result
        assert "errors" in result

    def test_run_with_custom_tools(self):
        def sinyal(sym, ctx):
            return {"ps_score": 90, "teknik": "AL", "haber": "pozitif"}

        def risk(sym, ctx, sinyal):
            return {"risk_etiketi": "UYGUN", "var": 0.01}

        def strateji(sym, ctx, sinyal, risk, debate):
            return {"verdict": "ONAY", "reason": "test"}

        wf = AgentWorkflow(sinyal_tool=sinyal, risk_tool=risk, strateji_tool=strateji)
        result = wf.run(symbol="THYAO", context={"makro": "BOGA"})
        assert result["final_decision"]["verdict"] == "ONAY"
        assert result["sinyal"]["ps_score"] == 90
        assert result["risk"]["risk_etiketi"] == "UYGUN"

    def test_run_risk_red(self):
        def sinyal(sym, ctx):
            return {"ps_score": 30, "teknik": "SAT", "haber": "negatif"}

        def risk(sym, ctx, sinyal):
            return {"risk_etiketi": "RED", "var": 0.05}

        def strateji(sym, ctx, sinyal, risk, debate):
            return {"verdict": "RED", "reason": risk.get("risk_etiketi")}

        wf = AgentWorkflow(sinyal_tool=sinyal, risk_tool=risk, strateji_tool=strateji)
        result = wf.run(symbol="THYAO", context={"makro": "AYI"})
        assert result["final_decision"]["verdict"] == "RED"

    def test_checkpoint_saved(self):
        with TemporaryDirectory() as td:
            wf = AgentWorkflow(checkpoint_dir=Path(td))
            wf.run(symbol="THYAO", context={"makro": "BOGA"})
            ck = wf.checkpoint.list_checkpoints()
            assert len(ck) >= 1
            latest = wf.load_checkpoint("THYAO")
            assert latest is not None
            assert latest["symbol"] == "THYAO"

    def test_risk_router_continue(self):
        state = AgentState()
        state.risk_output = {"risk_etiketi": "UYGUN"}
        assert AgentWorkflow._risk_router(state) == "continue"

    def test_risk_router_stop(self):
        state = AgentState()
        state.risk_output = {"risk_etiketi": "RED"}
        assert AgentWorkflow._risk_router(state) == "stop"

    def test_state_log(self):
        state = AgentState(symbol="THYAO")
        state.log("Sinyal", "test", "detail")
        assert len(state.logs) == 1
        assert state.logs[0]["agent"] == "Sinyal"

    def test_debate_integration(self):
        def sinyal(sym, ctx):
            return {"ps_score": 80, "teknik": "AL", "haber": "pozitif"}

        def risk(sym, ctx, sinyal):
            return {"risk_etiketi": "UYGUN", "var": 0.01}

        def strateji(sym, ctx, sinyal, risk, debate):
            return {"verdict": "ONAY" if debate.get("consensus_score", 0) >= 50 else "RED"}

        wf = AgentWorkflow(sinyal_tool=sinyal, risk_tool=risk, strateji_tool=strateji)
        result = wf.run(symbol="THYAO", context={"makro": "BOGA"})
        assert "debate" in result
        if result["debate"]:
            assert "consensus_score" in result["debate"]

    def test_state_to_dict(self):
        state = AgentState(symbol="X", sinyal_output={"a": 1}, risk_output={"b": 2})
        d = AgentWorkflow._state_to_dict(state)
        assert d["sinyal"] == {"a": 1}
        assert d["risk"] == {"b": 2}

    def test_node_sinyal(self):
        wf = AgentWorkflow()
        state = AgentState(symbol="THYAO")
        result = wf._node_sinyal(state)
        assert result.sinyal_output["symbol"] == "THYAO"
        assert len(result.logs) == 1

    def test_node_risk(self):
        wf = AgentWorkflow()
        state = AgentState(symbol="THYAO", sinyal_output={"ps_score": 80})
        result = wf._node_risk(state)
        assert "risk_etiketi" in result.risk_output

    def test_node_debate(self):
        wf = AgentWorkflow()
        state = AgentState(
            symbol="THYAO",
            sinyal_output={"ps_score": 80, "teknik": "AL", "haber": "pozitif"},
            risk_output={"risk_etiketi": "UYGUN"},
            context={"makro": "BOGA"},
        )
        result = wf._node_debate(state)
        assert "consensus_score" in result.debate_output

    def test_node_strateji(self):
        wf = AgentWorkflow()
        state = AgentState(
            symbol="THYAO",
            sinyal_output={"ps_score": 80},
            risk_output={"risk_etiketi": "UYGUN"},
            debate_output={"consensus_score": 70},
        )
        result = wf._node_strateji(state)
        assert result.final_decision["verdict"] == "ONAY"

    def test_node_checkpoint(self):
        with TemporaryDirectory() as td:
            wf = AgentWorkflow(checkpoint_dir=Path(td))
            state = AgentState(symbol="THYAO", final_decision={"verdict": "ONAY"})
            result = wf._node_checkpoint(state)
            assert any(l["agent"] == "Checkpoint" for l in result.logs)

    def test_build_graph_no_langgraph(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("agents.langgraph_workflow.LANGGRAPH_AVAILABLE", False)
            wf = AgentWorkflow()
            assert wf._graph is None

    def test_fallback_run(self):
        wf = AgentWorkflow()
        result = wf._fallback_run("THYAO", {"makro": "BOGA"})
        assert "final_decision" in result
        assert "logs" in result
        assert "errors" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
