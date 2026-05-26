"""
langgraph_workflow.py — LangGraph tabanli ajan orkestrasyonu.
tradingagents'tan entegre edilmistir.

Kullanim:
    from agents.langgraph_workflow import AgentWorkflow
    wf = AgentWorkflow()
    result = wf.run(symbol="THYAO", context={"makro": "BOGA"})

Not: LangGraph kurulu degilse mevcut AgentOrchestrator fallback olarak calisir.
"""
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

from typing import Optional, Callable, Any
from dataclasses import dataclass, field

# LangGraph opsiyonel bagimlilik
try:
    from langgraph.graph import StateGraph, END

    LANGGRAPH_AVAILABLE = True
except Exception:
    StateGraph = None
    END = None
    LANGGRAPH_AVAILABLE = False

from agents.orchestrator import AgentOrchestrator
from agents.debate_panel import DebatePanel
from agents.checkpoint import CheckpointManager


@dataclass
class AgentState:
    """
    LangGraph dugumleri arasinda tasinan durum yapisi.
    """

    symbol: str = ""
    context: dict = field(default_factory=dict)
    sinyal_output: dict = field(default_factory=dict)
    risk_output: dict = field(default_factory=dict)
    debate_output: dict = field(default_factory=dict)
    final_decision: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    logs: list[dict] = field(default_factory=list)

    def log(self, agent: str, action: str, detail: str = ""):
        self.logs.append({"agent": agent, "action": action, "detail": detail})


class AgentWorkflow:
    """
    LangGraph StateGraph ile 3 ajan akisi:
    Girdi -> Sinyal -> Risk -> Strateji -> Cikti

    Conditional edges: Risk RED verirse akis Strateji'ye gitmeden durur.
    """

    def __init__(
        self,
        sinyal_tool: Optional[Callable] = None,
        risk_tool: Optional[Callable] = None,
        strateji_tool: Optional[Callable] = None,
        checkpoint_dir: Optional[Path] = None,
    ):
        self.sinyal_tool = sinyal_tool or self._default_sinyal
        self.risk_tool = risk_tool or self._default_risk
        self.strateji_tool = strateji_tool or self._default_strateji
        self.checkpoint = CheckpointManager(checkpoint_dir)
        self._graph = None
        if LANGGRAPH_AVAILABLE:
            self._build_graph()
        else:
            self._fallback = AgentOrchestrator()

    # ---- Default tool stubs (override ile degistirilebilir) ----

    @staticmethod
    def _default_sinyal(symbol: str, context: dict) -> dict:
        return {"symbol": symbol, "ps_score": 50, "teknik": "N/A", "haber": "N/A", "mirofish": False}

    @staticmethod
    def _default_risk(symbol: str, context: dict, sinyal: dict) -> dict:
        return {"symbol": symbol, "risk_etiketi": "UYGUN", "var": 0.01, "kelly": 0.02}

    @staticmethod
    def _default_strateji(symbol: str, context: dict, sinyal: dict, risk: dict, debate: dict) -> dict:
        if risk.get("risk_etiketi") == "RED":
            return {"symbol": symbol, "verdict": "RED", "reason": "Risk ajani RED verdi"}
        if debate.get("consensus_score", 0) < 50:
            return {"symbol": symbol, "verdict": "RED", "reason": "Consensus dusuk"}
        return {"symbol": symbol, "verdict": "ONAY", "reason": "3/3 onay"}

    # ---- LangGraph builder ----

    def _build_graph(self):
        if not LANGGRAPH_AVAILABLE:
            return

        builder = StateGraph(AgentState)

        # Dugumler
        builder.add_node("sinyal", self._node_sinyal)
        builder.add_node("risk", self._node_risk)
        builder.add_node("debate", self._node_debate)
        builder.add_node("strateji", self._node_strateji)
        builder.add_node("checkpoint_save", self._node_checkpoint)

        # Kenarlar
        builder.set_entry_point("sinyal")
        builder.add_edge("sinyal", "risk")
        builder.add_conditional_edges(
            "risk",
            self._risk_router,
            {
                "continue": "debate",
                "stop": "strateji",
            },
        )
        builder.add_edge("debate", "strateji")
        builder.add_edge("strateji", "checkpoint_save")
        builder.add_edge("checkpoint_save", END)

        self._graph = builder.compile()

    def _node_sinyal(self, state: AgentState) -> AgentState:
        try:
            result = self.sinyal_tool(state.symbol, state.context)
            state.sinyal_output = result
            state.log("Sinyal", "analiz_tamamlandi", f"PS={result.get('ps_score')}")
        except Exception as e:
            state.errors.append(f"Sinyal hatasi: {e}")
            state.log("Sinyal", "hata", str(e))
        return state

    def _node_risk(self, state: AgentState) -> AgentState:
        try:
            result = self.risk_tool(state.symbol, state.context, state.sinyal_output)
            state.risk_output = result
            state.log("Risk", "kontrol_tamamlandi", f"Etiket={result.get('risk_etiketi')}")
        except Exception as e:
            state.errors.append(f"Risk hatasi: {e}")
            state.log("Risk", "hata", str(e))
        return state

    def _node_debate(self, state: AgentState) -> AgentState:
        try:
            bull = {
                "teknik": state.sinyal_output.get("teknik", "N/A"),
                "haber": state.sinyal_output.get("haber", "N/A"),
                "ps": state.sinyal_output.get("ps_score", 50),
                "risk": state.risk_output.get("risk_etiketi", "UYGUN"),
                "makro": state.context.get("makro", "YAN"),
            }
            bear = {
                "teknik": "SAT",
                "haber": "notr",
                "ps": max(0, 100 - bull["ps"]),
                "risk": state.risk_output.get("risk_etiketi", "UYGUN"),
                "makro": state.context.get("makro", "YAN"),
            }
            panel = DebatePanel(symbol=state.symbol)
            result = panel.debate(bull_args=bull, bear_args=bear)
            state.debate_output = result
            state.log("Debate", "tartisma_tamamlandi", f"Consensus={result.get('consensus_score')}")
        except Exception as e:
            state.errors.append(f"Debate hatasi: {e}")
            state.log("Debate", "hata", str(e))
        return state

    def _node_strateji(self, state: AgentState) -> AgentState:
        try:
            result = self.strateji_tool(
                state.symbol, state.context, state.sinyal_output, state.risk_output, state.debate_output
            )
            state.final_decision = result
            state.log("Strateji", "karar", result.get("verdict", "N/A"))
        except Exception as e:
            state.errors.append(f"Strateji hatasi: {e}")
            state.log("Strateji", "hata", str(e))
        return state

    def _node_checkpoint(self, state: AgentState) -> AgentState:
        try:
            self.checkpoint.save(
                state={
                    "symbol": state.symbol,
                    "sinyal_output": state.sinyal_output,
                    "risk_output": state.risk_output,
                    "debate_output": state.debate_output,
                    "final_decision": state.final_decision,
                    "errors": state.errors,
                    "logs": state.logs,
                },
                label=f"{state.symbol}_workflow",
            )
            state.log("Checkpoint", "kaydedildi")
        except Exception as e:
            state.errors.append(f"Checkpoint hatasi: {e}")
        return state

    @staticmethod
    def _risk_router(state: AgentState) -> str:
        if state.risk_output.get("risk_etiketi") == "RED":
            return "stop"
        return "continue"

    # ---- Public API ----

    def run(self, symbol: str, context: Optional[dict] = None) -> dict:
        """
        Workflow'u calistir. LangGraph yoksa fallback orkestratore devreder.

        Donus: {"final_decision": dict, "sinyal": dict, "risk": dict, "debate": dict, "logs": list, "errors": list}
        """
        if not LANGGRAPH_AVAILABLE or self._graph is None:
            return self._fallback_run(symbol, context)

        initial_state = AgentState(symbol=symbol, context=context or {})
        final_state = self._graph.invoke(initial_state)
        return self._state_to_dict(final_state)

    def _fallback_run(self, symbol: str, context: Optional[dict] = None) -> dict:
        """
        LangGraph yoksa araclari sirasiyla calistir ve checkpoint kaydet.
        """
        ctx = context or {}
        logs = []
        errors = []

        try:
            sinyal_out = self.sinyal_tool(symbol, ctx)
            logs.append({"agent": "Sinyal", "action": "analiz", "detail": str(sinyal_out.get("ps_score", "N/A"))})
        except Exception as e:
            sinyal_out = {}
            errors.append(f"Sinyal hatasi: {e}")

        try:
            risk_out = self.risk_tool(symbol, ctx, sinyal_out)
            logs.append({"agent": "Risk", "action": "kontrol", "detail": risk_out.get("risk_etiketi", "N/A")})
        except Exception as e:
            risk_out = {}
            errors.append(f"Risk hatasi: {e}")

        try:
            bull = {
                "teknik": sinyal_out.get("teknik", "N/A"),
                "haber": sinyal_out.get("haber", "N/A"),
                "ps": sinyal_out.get("ps_score", 50),
                "risk": risk_out.get("risk_etiketi", "UYGUN"),
                "makro": ctx.get("makro", "YAN"),
            }
            bear = {
                "teknik": "SAT",
                "haber": "notr",
                "ps": max(0, 100 - bull["ps"]),
                "risk": risk_out.get("risk_etiketi", "UYGUN"),
                "makro": ctx.get("makro", "YAN"),
            }
            panel = DebatePanel(symbol=symbol)
            debate_out = panel.debate(bull_args=bull, bear_args=bear)
            logs.append({"agent": "Debate", "action": "tartisma", "detail": str(debate_out.get("consensus_score"))})
        except Exception as e:
            debate_out = {}
            errors.append(f"Debate hatasi: {e}")

        try:
            decision = self.strateji_tool(symbol, ctx, sinyal_out, risk_out, debate_out)
            logs.append({"agent": "Strateji", "action": "karar", "detail": decision.get("verdict", "N/A")})
        except Exception as e:
            decision = {"verdict": "RED", "reason": f"Strateji hatasi: {e}"}
            errors.append(f"Strateji hatasi: {e}")

        try:
            self.checkpoint.save(
                state={
                    "symbol": symbol,
                    "sinyal_output": sinyal_out,
                    "risk_output": risk_out,
                    "debate_output": debate_out,
                    "final_decision": decision,
                    "errors": errors,
                    "logs": logs,
                },
                label=f"{symbol}_workflow",
            )
            logs.append({"agent": "Checkpoint", "action": "kaydet", "detail": "fallback"})
        except Exception as e:
            errors.append(f"Checkpoint hatasi: {e}")

        return {
            "final_decision": decision,
            "sinyal": sinyal_out,
            "risk": risk_out,
            "debate": debate_out,
            "logs": logs,
            "errors": errors,
        }

    @staticmethod
    def _state_to_dict(state: AgentState) -> dict:
        return {
            "final_decision": state.final_decision,
            "sinyal": state.sinyal_output,
            "risk": state.risk_output,
            "debate": state.debate_output,
            "logs": state.logs,
            "errors": state.errors,
        }

    def load_checkpoint(self, symbol: str) -> Optional[dict]:
        """
        Son checkpoint'i yukle.
        """
        return self.checkpoint.load_by_label(f"{symbol}_workflow")


if __name__ == "__main__":
    wf = AgentWorkflow()
    result = wf.run(symbol="THYAO", context={"makro": "BOGA"})
    print("Workflow sonuc:")
    print(result)
